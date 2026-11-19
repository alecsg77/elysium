#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
prefix="orca-storage-test-$$"
home_volume="$prefix-home"
project_volume="$prefix-project"
container="$prefix-worker"
fixture=$(mktemp -d)
cache_test=${ORCA_CACHE_TEST:-false}
registry="$prefix-registry"
git_pid=
cache_args=()
worker_image=ghcr.io/coder/envbuilder:1.3.0
cleanup() {
  docker rm -f "$container" "$registry" >/dev/null 2>&1 || true
  if [[ -n "$git_pid" ]]; then kill "$git_pid" 2>/dev/null || true; wait "$git_pid" 2>/dev/null || true; fi
  docker volume rm "$home_volume" "$project_volume" >/dev/null 2>&1 || true
  if [[ "$worker_image" == 127.0.0.1:*@sha256:* ]]; then docker image rm "$worker_image" >/dev/null 2>&1 || true; fi
  rm -rf -- "$fixture"
}
trap cleanup EXIT
mkdir -p "$fixture/.devcontainer"
cat > "$fixture/.devcontainer/devcontainer.json" <<'JSON'
{"build":{"dockerfile":"Dockerfile"},"containerUser":"coder","remoteUser":"coder"}
JSON
cat > "$fixture/.devcontainer/Dockerfile" <<'DOCKERFILE'
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends passwd util-linux ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 1000 --create-home coder
RUN printf build-once-fixture > /opt/orca-build-marker
USER coder
DOCKERFILE

if [[ "$cache_test" != false ]]; then
  git -C "$fixture" init -q --initial-branch=main
  git -C "$fixture" add .
  git -C "$fixture" -c user.name=Fixture -c user.email=fixture@example.com commit -qm fixture
  git_port=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')
  git daemon --reuseaddr --export-all --listen=127.0.0.1 --port="$git_port" --base-path="$fixture" "$fixture" &
  git_pid=$!
  docker run -d --name "$registry" -p 127.0.0.1::5000 registry:3 >/dev/null
  registry_port=$(docker port "$registry" 5000/tcp | cut -d: -f2)
  cache_args=(--network host
    -e "ENVBUILDER_GIT_URL=git://127.0.0.1:$git_port/"
    -e "ENVBUILDER_CACHE_REPO=127.0.0.1:$registry_port/devcontainer"
    -e ENVBUILDER_INSECURE=true
    -e ENVBUILDER_REMOTE_REPO_BUILD_MODE=true
    -e "ENVBUILDER_PUSH_IMAGE=$([[ "$cache_test" == full ]] && echo true || echo false)"
    -e ENVBUILDER_EXIT_ON_PUSH_FAILURE=true)
fi

docker volume create "$home_volume" >/dev/null
docker volume create "$project_volume" >/dev/null
docker run --rm --mount "type=volume,src=$project_volume,dst=/data" \
  --mount "type=bind,src=$fixture,dst=/fixture,readonly" \
  debian:bookworm-slim sh -ec 'mkdir -p /data/project; cp -a /fixture/. /data/project/; chown -R 0:0 /data/project'
docker run --rm --mount "type=volume,src=$home_volume,dst=/data" \
  debian:bookworm-slim sh -ec 'mkdir -p /data/.codex; printf synthetic-auth-fixture > /data/.codex/auth.json; chown -R 1000:1000 /data'

start_worker() {
  docker run -d --name "$container" --privileged "${cache_args[@]}" \
    --mount "type=volume,src=$home_volume,dst=/home/coder" \
    --mount "type=volume,src=$project_volume,dst=/workspaces" \
    -e ENVBUILDER_WORKSPACE_FOLDER=/workspaces/project \
    -e ENVBUILDER_IGNORE_PATHS=/var/run,/product_uuid,/product_name,/home/coder,/workspaces \
    -e ENVBUILDER_EXIT_ON_BUILD_FAILURE=true \
    -e ENVBUILDER_SETUP_SCRIPT="$(cat "$root/scripts/check-user.sh")" \
    -e ENVBUILDER_INIT_SCRIPT='test "$HOME" = /home/coder; exec sleep infinity' \
    "$worker_image" >/dev/null
  for _attempt in $(seq 1 120); do
    if docker exec --user coder "$container" test -f /etc/debian_version 2>/dev/null \
      && docker top "$container" -eo pid,comm | awk 'NR > 1 { print $2 }' | grep -qx sleep; then
      return
    fi
    if [[ "$(docker inspect --format '{{.State.Running}}' "$container")" != true ]]; then
      docker logs --tail 30 "$container"
      return 1
    fi
    sleep 2
  done
  echo 'Envbuilder did not become ready.' >&2
  return 1
}

probe_cache() {
  local expected=$1
  local terraform_bin=${TERRAFORM_BIN:-terraform}
  mkdir -p "$fixture/probe"
  cat > "$fixture/probe/main.tf" <<'TERRAFORM'
terraform {
  required_providers {
    envbuilder = { source = "coder/envbuilder", version = "1.0.0" }
  }
}
variable "git_url" { type = string }
variable "cache_repo" { type = string }
resource "envbuilder_cached_image" "test" {
  builder_image = "ghcr.io/coder/envbuilder:1.3.0"
  git_url       = var.git_url
  cache_repo    = var.cache_repo
  insecure      = true
  extra_env = {
    ENVBUILDER_DEVCONTAINER_DIR       = ".devcontainer"
    ENVBUILDER_IGNORE_PATHS           = "/var/run,/product_uuid,/product_name,/home/coder,/workspaces"
    ENVBUILDER_EXIT_ON_BUILD_FAILURE  = "true"
    ENVBUILDER_REMOTE_REPO_BUILD_MODE = "true"
    ENVBUILDER_PUSH_IMAGE             = "true"
  }
}
output "exists" { value = envbuilder_cached_image.test.exists }
output "image" { value = envbuilder_cached_image.test.image }
TERRAFORM
  "$terraform_bin" -chdir="$fixture/probe" init -backend=false -input=false -plugin-dir="$root/.terraform/providers" > "$fixture/probe-init.log" 2>&1
  TF_LOG=INFO TF_LOG_PATH="$fixture/provider.log" "$terraform_bin" -chdir="$fixture/probe" apply -auto-approve -input=false \
    -replace=envbuilder_cached_image.test \
    -var="git_url=file://$fixture" \
    -var="cache_repo=127.0.0.1:$registry_port/devcontainer" > "$fixture/probe-apply.log" 2>&1
  if [[ "$("$terraform_bin" -chdir="$fixture/probe" output -raw exists)" != "$expected" ]]; then
    cat "$fixture/probe-apply.log" >&2
    tail -45 "$fixture/provider.log" >&2
    return 1
  fi
  worker_image=$("$terraform_bin" -chdir="$fixture/probe" output -raw image)
}
if [[ "$cache_test" == full ]]; then probe_cache false; fi
cold_started=$SECONDS
start_worker
cold_seconds=$((SECONDS - cold_started))
docker exec --user coder "$container" sh -ec '
  mkdir -p /home/coder/.codex /home/coder/.config/orca /home/coder/.local/share/opencode
  test "$(cat /home/coder/.codex/auth.json)" = synthetic-auth-fixture
  printf settings-fixture > /home/coder/.config/orca/settings.json
  printf history-fixture > /home/coder/.local/share/opencode/history-fixture
  printf project-fixture > /workspaces/project/uncommitted-fixture
'
if [[ "$cache_test" != false ]]; then
  docker logs "$container" > "$fixture/cold.log" 2>&1
fi
if [[ "$cache_test" == full ]]; then probe_cache true; fi
# Remove the whole container to force a fresh in-place image build on the same data.
docker rm -f "$container" >/dev/null
warm_started=$SECONDS
start_worker
warm_seconds=$((SECONDS - warm_started))
docker exec --user coder "$container" sh -ec '
  test "$(cat /home/coder/.codex/auth.json)" = synthetic-auth-fixture
  test "$(cat /home/coder/.config/orca/settings.json)" = settings-fixture
  test "$(cat /home/coder/.local/share/opencode/history-fixture)" = history-fixture
  test "$(cat /workspaces/project/uncommitted-fixture)" = project-fixture
'
printf '%s\n' 'PASS: complete home and project data survived container replacement and rebuild.'

if [[ "$cache_test" != false ]]; then
  docker logs "$container" > "$fixture/warm.log" 2>&1
  if [[ "$cache_test" == full ]]; then
    [[ "$worker_image" == *@sha256:* ]]
    if grep -q 'Building image' "$fixture/warm.log"; then
      cat "$fixture/warm.log" >&2
      echo 'The cached complete image unexpectedly rebuilt the devcontainer.' >&2
      exit 1
    fi
  else
    grep -q 'Found cached layer, extracting' "$fixture/warm.log"
  fi
  if grep -q 'No cached layer found' "$fixture/warm.log"; then
    cat "$fixture/warm.log" >&2
    echo 'The unchanged second build missed a cached layer.' >&2
    exit 1
  fi
  docker exec "$container" test -f /opt/orca-build-marker
  python3 - "$registry_port" <<'PYTHON'
import io
import json
import subprocess
import sys
import tarfile
import urllib.request

base = f"http://127.0.0.1:{sys.argv[1]}/v2/devcontainer"
def fetch(path, accept=None):
    request = urllib.request.Request(base + path, headers={"Accept": accept} if accept else {})
    return urllib.request.urlopen(request, timeout=30).read()

tags = json.loads(fetch("/tags/list"))["tags"]
assert tags, "No layers were published"
checked = set()
for tag in tags:
    manifest = json.loads(fetch("/manifests/" + tag, "application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json"))
    config = fetch("/blobs/" + manifest["config"]["digest"])
    assert b"synthetic-auth-fixture" not in config
    for layer in manifest["layers"]:
        digest = layer["digest"]
        if digest in checked:
            continue
        checked.add(digest)
        blob = fetch("/blobs/" + digest)
        if layer.get("mediaType", "").endswith("+zstd"):
            blob = subprocess.run(["zstd", "--decompress", "--stdout", "--quiet"], input=blob,
                                  stdout=subprocess.PIPE, check=True).stdout
        try:
            archive = tarfile.open(fileobj=io.BytesIO(blob), mode="r:*")
        except tarfile.ReadError:
            raise AssertionError((digest, layer.get("mediaType"), len(blob), blob[:20])) from None
        with archive:
            for entry in archive:
                path = entry.name.removeprefix("./").lstrip("/")
                assert not (path.startswith("home/coder/") or path.startswith("workspaces/")), path
                if entry.isfile():
                    content = archive.extractfile(entry).read()
                    assert b"synthetic-auth-fixture" not in content, path
                    assert b"project-fixture" not in content, path
print(f"PASS: {len(checked)} published layers exclude persistent home/project files and synthetic credentials.")
PYTHON
  printf 'PASS: cache mode %s (cold %ss, warm %ss).\n' "$cache_test" "$cold_seconds" "$warm_seconds"
fi
