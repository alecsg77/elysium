#!/usr/bin/env bash
set -euo pipefail

pid_file=/tmp/coder-orca-serve.pid
[[ -s "$pid_file" ]] || exit 0
read -r pid <"$pid_file"
[[ "$pid" =~ ^[1-9][0-9]*$ ]] || exit 0

# A stale PID must never signal an unrelated process.
cli=$(readlink -f "$HOME/.local/bin/orca-ide")
launcher="${cli%/resources/bin/orca-ide}/orca-ide"
[[ $(readlink "/proc/$pid/exe") == "$launcher" ]] || exit 0

kill -TERM "$pid"
for ((attempt = 0; attempt < 15; attempt++)); do
  [[ -e "$ORCA_USER_DATA_PATH/orcad.lock" ]] || exit 0
  sleep 1
done
echo "Orca did not release its profile lock during shutdown." >&2
exit 1
