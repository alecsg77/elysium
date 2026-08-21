#!/usr/bin/env bash
# Local regression check:
#   bash apps/kyrion/ai/validate-openclaw-restore-drill-verifier.sh
#
# The verifier is generated into a ConfigMap and therefore passes through the
# apps Kustomization's Flux post-build substitution. Keep JavaScript template
# expressions out of the generated source: Flux treats raw ${...} as variables.
set -euo pipefail

script_dir="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(git -C "$script_dir" rev-parse --show-toplevel)"
cd "$repo_root"

verifier="apps/kyrion/ai/openclaw-restore-drill-verify.js"

if grep -Fq "\${" "$verifier"; then
  printf 'Flux-unsafe template expression found in %s\n' "$verifier" >&2
  exit 1
fi

node --check "$verifier"
kustomize build apps/kyrion/ai | flux envsubst >/dev/null
