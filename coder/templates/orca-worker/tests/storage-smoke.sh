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
cache_args=()
network="$prefix-network"
cleanup() {
  docker rm -f "$container" "$registry" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  docker volume rm "$home_volume" "$project_volume" >/dev/null 2>&1 || true
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
USER coder
DOCKERFILE

if [[ "$cache_test" == true ]]; then
  docker network create "$network" >/dev/null
  docker run -d --name "$registry" --network "$network" --network-alias registry.test.local \
    -p 127.0.0.1::5000 registry:3 >/dev/null
  registry_port=$(docker port "$registry" 5000/tcp | cut -d: -f2)
  cache_args=(--network "$network" -e ENVBUILDER_CACHE_REPO=registry.test.local:5000/devcontainer)
fi

docker volume create "$home_volume" >/dev/null
docker volume create "$project_volume" >/dev/null
docker run --rm --mount "type=volume,src=$project_volume,dst=/data" \
  --mount "type=bind,src=$fixture,dst=/fixture,readonly" \
  debian:bookworm-slim sh -ec 'mkdir -p /data/project; cp -a /fixture/. /data/project/; printf project-fixture > /data/project/uncommitted-fixture; chown -R 0:0 /data/project'
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
    ghcr.io/coder/envbuilder:1.3.0 >/dev/null
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

start_worker
docker exec --user coder "$container" sh -ec '
  mkdir -p /home/coder/.codex /home/coder/.config/orca /home/coder/.local/share/opencode
  test "$(cat /home/coder/.codex/auth.json)" = synthetic-auth-fixture
  printf settings-fixture > /home/coder/.config/orca/settings.json
  printf history-fixture > /home/coder/.local/share/opencode/history-fixture
  test "$(cat /workspaces/project/uncommitted-fixture)" = project-fixture
'
# Remove the whole container to force a fresh in-place image build on the same data.
docker rm -f "$container" >/dev/null
start_worker
docker exec --user coder "$container" sh -ec '
  test "$(cat /home/coder/.codex/auth.json)" = synthetic-auth-fixture
  test "$(cat /home/coder/.config/orca/settings.json)" = settings-fixture
  test "$(cat /home/coder/.local/share/opencode/history-fixture)" = history-fixture
  test "$(cat /workspaces/project/uncommitted-fixture)" = project-fixture
'
printf '%s\n' 'PASS: complete home and project data survived container replacement and rebuild.'

if [[ "$cache_test" == true ]]; then
  docker logs "$container" > "$fixture/warm.log" 2>&1
  if ! grep -q 'Found cached layer, extracting' "$fixture/warm.log"; then
    cat "$fixture/warm.log" >&2
    echo 'The second build did not reuse registry layers.' >&2
    exit 1
  fi
  if grep -q 'No cached layer found' "$fixture/warm.log"; then
    cat "$fixture/warm.log" >&2
    echo 'The unchanged second build missed a cached layer.' >&2
    exit 1
  fi
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
  printf '%s\n' 'PASS: unchanged second build reused layers from the HTTP registry.'
fi
