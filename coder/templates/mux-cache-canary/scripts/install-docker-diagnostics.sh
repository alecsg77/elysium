#!/usr/bin/env bash
# Installs persistent, non-destructive Docker/BuildKit diagnostics and an
# opt-in Dev Containers wrapper. The wrapper never mutates Docker state.
set -euo pipefail

BIN_DIR="$HOME/.local/bin"
install -d -m 0755 "$BIN_DIR"

cat >"$BIN_DIR/collect-mux-docker-state" <<'COLLECTOR'
#!/usr/bin/env bash
set -uo pipefail

label="${1:-manual}"
root="${MUX_DOCKER_DIAGNOSTICS_DIR:-$HOME/.mux/docker-diagnostics}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="$root/${timestamp}-${label}"
mkdir -p "$run_dir"
umask 077

run() {
  local name="$1"
  shift
  {
    printf 'captured_at=%s\n' "$(date -u --iso-8601=seconds)"
    printf 'command='
    printf '%q ' "$@"
    printf '\n\n'
    "$@"
  } >"$run_dir/$name.log" 2>&1 || {
    local status=$?
    printf '\ncommand_exit=%s\n' "$status" >>"$run_dir/$name.log"
  }
}

run_shell() {
  local name="$1"
  local command="$2"
  run "$name" bash -lc "$command"
}

run docker-version docker version
run docker-info docker info
run docker-buildx-version docker buildx version
run docker-buildx-ls docker buildx ls
run docker-builder-du docker builder du --verbose
run docker-ps docker ps -a --no-trunc
run docker-system-df docker system df -v
run mount-docker findmnt -T /var/lib/docker -o TARGET,SOURCE,FSTYPE,OPTIONS
run mount-coder-docker findmnt -T /var/lib/coder/docker -o TARGET,SOURCE,FSTYPE,OPTIONS
run stat-docker stat -c '%n uid=%u gid=%g mode=%a' /var/lib/docker
run stat-coder-docker stat -c '%n uid=%u gid=%g mode=%a' /var/lib/coder/docker
run disk-space df -h /var/lib/docker /var/lib/coder/docker
run inode-space df -i /var/lib/docker /var/lib/coder/docker
run_shell docker-journal "sudo -n journalctl -u docker --no-pager -n 500 | grep -Ei 'content digest|snapshot|extract|overlay|only one connection|EOVERFLOW|ENOSPC|start|stop|shutdown' || true"
run_shell workspace-identity "printf 'hostname='; hostname; printf 'workspace_build='; coder list --output json 2>/dev/null | jq -r '.[] | select(.name==\"mux\" or .name==\"mux-cache-canary\") | [.name, .latest_build.build_number, .latest_build.template_version_id] | @tsv' || true"

if [ -n "${MUX_DOCKER_DIAGNOSTICS_SOURCE_LOG:-}" ] && [ -f "$MUX_DOCKER_DIAGNOSTICS_SOURCE_LOG" ]; then
  cp "$MUX_DOCKER_DIAGNOSTICS_SOURCE_LOG" "$run_dir/devcontainer.log"
  awk '/=> ERROR|ERROR:|Error: Command failed|failed to (extract layer|prepare|build|solve)/ { print; if (++count == 1) exit }' \
    "$MUX_DOCKER_DIAGNOSTICS_SOURCE_LOG" >"$run_dir/first-build-error.log" || true
fi

printf '%s\n' "$run_dir"
COLLECTOR
chmod 0755 "$BIN_DIR/collect-mux-docker-state"

cat >"$BIN_DIR/devcontainer-observed" <<'WRAPPER'
#!/usr/bin/env bash
set -o pipefail

real_devcontainer="${DEVCONTAINER_BIN:-/tmp/coder-script-data/bin/devcontainer}"
if [ ! -x "$real_devcontainer" ]; then
  echo "devcontainer-observed: expected Dev Containers CLI at $real_devcontainer" >&2
  exit 127
fi

root="${MUX_DOCKER_DIAGNOSTICS_DIR:-$HOME/.mux/docker-diagnostics}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="$root/${timestamp}-devcontainer-command"
mkdir -p "$run_dir"
printf '%q ' "$real_devcontainer" "$@" >"$run_dir/command.txt"
printf '\n' >>"$run_dir/command.txt"

"$real_devcontainer" "$@" 2>&1 | tee "$run_dir/devcontainer.log"
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then
  MUX_DOCKER_DIAGNOSTICS_SOURCE_LOG="$run_dir/devcontainer.log" \
    "$HOME/.local/bin/collect-mux-docker-state" devcontainer-failed >/dev/null || true
fi
exit "$status"
WRAPPER
chmod 0755 "$BIN_DIR/devcontainer-observed"

printf '%s\n' "Installed collect-mux-docker-state and devcontainer-observed in $BIN_DIR"
