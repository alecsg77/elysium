#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo 'Usage: bash scripts/ci/check-image-tag.sh --image REFERENCE --input-hash SHA256 --output PATH'
  echo 'Writes true for a missing tag, false for identical published inputs; rejects reuse and registry errors.'
}

image_ref=''
input_hash=''
output_path=''
while (($#)); do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --image|--input-hash|--output)
      (($# >= 2)) || { usage >&2; exit 2; }
      case "$1" in
        --image) image_ref=$2 ;;
        --input-hash) input_hash=$2 ;;
        --output) output_path=$2 ;;
      esac
      shift 2
      ;;
    *) usage >&2; exit 2 ;;
  esac
done
[[ -n "$image_ref" && "$input_hash" =~ ^[a-f0-9]{64}$ && -n "$output_path" ]] || {
  usage >&2
  exit 2
}
config_path="${output_path}.config"
error_path="${output_path}.error"
trap 'rm -f -- "$config_path" "$error_path"' EXIT

if docker buildx imagetools inspect "$image_ref" --format '{{json .Image}}' >"$config_path" 2>"$error_path"; then
  published_hash=$(jq -r '.config.Labels["dev.elysium.build-inputs"] // empty' "$config_path")
  [[ "$published_hash" == "$input_hash" ]] || {
    echo "::error::${image_ref} already exists with different or unknown inputs; use a new SemVer version." >&2
    exit 1
  }
  echo false >"$output_path"
elif grep -Eq 'manifest unknown|: not found$' "$error_path"; then
  echo true >"$output_path"
else
  cat "$error_path" >&2
  exit 1
fi
