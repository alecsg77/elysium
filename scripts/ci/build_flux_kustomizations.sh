#!/usr/bin/env bash
# Build the fixed Flux Kustomizations evaluated by PR Gate.
set -euo pipefail

root="."
output="rendered"

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
    *)
      echo "Usage: $0 [--root DIRECTORY] [--output DIRECTORY]" >&2
      exit 2
      ;;
  esac
done

root="$(cd "$root" && pwd)"
mkdir -p "$output"
output="$(cd "$output" && pwd)"

cd "$root"
flux build kustomization apps \
  --path ./apps/kyrion \
  --kustomization-file clusters/kyrion/apps.yaml \
  --dry-run > "$output/flux-apps.yaml"
flux build kustomization infra-controllers \
  --path ./clusters/kyrion/infrastructure/controllers \
  --kustomization-file clusters/kyrion/infrastructure.yaml \
  --dry-run > "$output/flux-infra-controllers.yaml"
flux build kustomization infra-configs \
  --path ./clusters/kyrion/infrastructure/configs \
  --kustomization-file clusters/kyrion/infrastructure.yaml \
  --dry-run > "$output/flux-infra-configs.yaml"
flux build kustomization monitoring-controllers \
  --path ./clusters/kyrion/monitoring/controllers \
  --kustomization-file clusters/kyrion/monitoring.yaml \
  --dry-run > "$output/flux-monitoring-controllers.yaml"
flux build kustomization monitoring-configs \
  --path ./monitoring/configs \
  --kustomization-file clusters/kyrion/monitoring.yaml \
  --dry-run > "$output/flux-monitoring-configs.yaml"
