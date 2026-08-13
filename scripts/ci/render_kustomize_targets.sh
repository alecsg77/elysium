#!/usr/bin/env bash
# Render the fixed PR Gate Kustomize target set without plugins or Helm inflation.
# This trusted helper treats the requested repository tree as inert Kustomize input.
set -euo pipefail

root="."
output="rendered"
temp_root="${RUNNER_TEMP:-/tmp}"

while (($#)); do
  case "$1" in
    --root)
      root="$2"
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
    *)
      echo "Usage: $0 [--root DIRECTORY] [--output DIRECTORY] [--temp-root DIRECTORY]" >&2
      exit 2
      ;;
  esac
done

root="$(cd "$root" && pwd)"
mkdir -p "$output"
output="$(cd "$output" && pwd)"
mkdir -p "$temp_root"
workspace="$(mktemp -d "$temp_root/kustomize-render.XXXXXX")"
trap 'rm -rf "$workspace"' EXIT

# Do not load Kustomize exec plugins/functions from the proposed checkout.
export KUSTOMIZE_PLUGIN_HOME="$workspace/disabled-kustomize-plugins"

targets=(
  clusters/kyrion
  apps/kyrion/ai
  apps/kyrion/airflow
  apps/kyrion/arkham
  apps/kyrion/coder
  apps/kyrion/default
  apps/kyrion/fission
  apps/kyrion/n8n
  apps/kyrion/raiplaysoundrss
  apps/kyrion/registry
  apps/kyrion/romm
  infrastructure/controllers
  infrastructure/configs
  clusters/kyrion/infrastructure/controllers
  clusters/kyrion/infrastructure/configs
  monitoring/controllers
  clusters/kyrion/monitoring/controllers
  monitoring/configs
)

for target in "${targets[@]}"; do
  source="$root/$target"
  test -d "$source"
  slug="${target//\//-}"
  if [[ ! -f "$source/kustomization.yaml" && ! -f "$source/kustomization.yml" && ! -f "$source/Kustomization" ]]; then
    temporary="$workspace/$slug"
    mkdir -p "$temporary"
    cp -a "$source/." "$temporary/"
    (
      cd "$temporary"
      kustomize create --autodetect --recursive
    )
    kustomize build "$temporary" > "$output/$slug.yaml"
  else
    kustomize build "$source" > "$output/$slug.yaml"
  fi
done
