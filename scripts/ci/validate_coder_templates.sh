#!/usr/bin/env bash
# Run Coder template Terraform validation without backend/session credentials.
# The helper is trusted; Terraform files under --root are proposed data.
set -euo pipefail

root="."
template_file=""

while (($#)); do
  case "$1" in
    --root)
      root="$2"
      shift 2
      ;;
    --template-file)
      template_file="$2"
      shift 2
      ;;
    *)
      echo "Usage: $0 --template-file FILE [--root DIRECTORY]" >&2
      exit 2
      ;;
  esac
done

test -n "$template_file"
root="$(cd "$root" && pwd)"
test -f "$template_file"

while IFS= read -r template; do
  test -n "$template"
  case "$template" in
    */*|.|..|*'..'*)
      echo "::error::Unsafe Coder template directory name: $template" >&2
      exit 1
      ;;
  esac
  directory="$root/coder/templates/$template"
  if [[ ! -d "$directory" ]]; then
    echo "::error::Changed Coder template was removed: coder/templates/$template" >&2
    exit 1
  fi
  terraform -chdir="$directory" fmt -check -recursive
  terraform -chdir="$directory" init -backend=false -input=false
  terraform -chdir="$directory" validate -no-color
done < "$template_file"
