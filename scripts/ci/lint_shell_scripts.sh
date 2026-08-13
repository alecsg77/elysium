#!/usr/bin/env bash
# Parse and ShellCheck shell scripts without sourcing or executing them.
set -euo pipefail

root="."
if [[ ${1:-} == "--root" ]]; then
  root="$2"
  shift 2
fi
if (($#)); then
  echo "Usage: $0 [--root DIRECTORY]" >&2
  exit 2
fi

root="$(cd "$root" && pwd)"
mapfile -d '' scripts < <(find "$root/scripts" -type f -name '*.sh' -print0 | sort -z)
test "${#scripts[@]}" -gt 0

for script in "${scripts[@]}"; do
  case "$(head -n 1 "$script")" in
    *"/bin/sh"*) sh -n "$script" ;;
    *) bash -n "$script" ;;
  esac
done
shellcheck "${scripts[@]}"
