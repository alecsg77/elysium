#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
prefix="orca-storage-test-$$"
home_volume="$prefix-home"
project_volume="$prefix-project"
container="$prefix-worker"
fixture=$(mktemp -d)
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
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

docker volume create "$home_volume" >/dev/null
docker volume create "$project_volume" >/dev/null
docker run --rm --mount "type=volume,src=$project_volume,dst=/data" \
  --mount "type=bind,src=$fixture,dst=/fixture,readonly" \
  debian:bookworm-slim sh -ec 'mkdir -p /data/project; cp -a /fixture/. /data/project/'
docker run --rm --mount "type=volume,src=$home_volume,dst=/data" \
  debian:bookworm-slim chown 1000:1000 /data

start_worker() {
  docker run -d --name "$container" --privileged \
    --mount "type=volume,src=$home_volume,dst=/home/coder" \
    --mount "type=volume,src=$project_volume,dst=/workspaces" \
    -e ENVBUILDER_WORKSPACE_FOLDER=/workspaces/project \
    -e ENVBUILDER_IGNORE_PATHS=/var/run,/product_uuid,/product_name,/home/coder \
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
  printf synthetic-auth-fixture > /home/coder/.codex/auth.json
  printf settings-fixture > /home/coder/.config/orca/settings.json
  printf history-fixture > /home/coder/.local/share/opencode/history-fixture
  printf project-fixture > /workspaces/project/uncommitted-fixture
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
