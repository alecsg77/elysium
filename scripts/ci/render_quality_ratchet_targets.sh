#!/usr/bin/env bash
# Render both trusted base and proposed GitOps trees for the quality ratchet.
# The workflow installs the fixed Kustomize and Flux binaries before this helper runs.
set -euo pipefail

usage() {
  echo "Usage: $0 --base-root DIRECTORY --head-root DIRECTORY --output DIRECTORY --temp-root DIRECTORY" >&2
}

base_root=""
head_root=""
output=""
temp_root=""

while (($#)); do
  case "$1" in
    --base-root)
      base_root="$2"
      shift 2
      ;;
    --head-root)
      head_root="$2"
      shift 2
      ;;
    --output)
      output="$2"
      shift 2
      ;;
    --temp-root)
      temp_root="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

for required in base_root head_root output temp_root; do
  test -n "${!required}" || {
    usage
    exit 2
  }
done

test -d "$base_root"
test -d "$head_root"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rm -rf -- "$output"
mkdir -p "$output/base-rendered" "$output/head-rendered"

bash "$script_dir/render_kustomize_targets.sh" \
  --root "$base_root" \
  --output "$output/base-rendered" \
  --temp-root "$temp_root"
bash "$script_dir/render_kustomize_targets.sh" \
  --root "$head_root" \
  --output "$output/head-rendered" \
  --temp-root "$temp_root"
bash "$script_dir/build_flux_kustomizations.sh" \
  --root "$base_root" \
  --output "$output/base-rendered"
bash "$script_dir/build_flux_kustomizations.sh" \
  --root "$head_root" \
  --output "$output/head-rendered"
