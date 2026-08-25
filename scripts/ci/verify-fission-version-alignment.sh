#!/usr/bin/env bash
# Verify that the independently consumed Fission pins describe one upstream
# release before Flux reconciles the platform or GitHub deploys function specs.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/ci/verify-fission-version-alignment.sh [--root PATH]

Validates that Fission's Helm chart, CRD Git-object pin, deployment CLI/checksum,
and Dev Container CLI pin are aligned to one stable Fission release. It also checks
that the chart declares the matching appVersion, the CRD pin resolves from the tag,
and the CLI checksum is published by that release.
EOF
}

fail() {
  printf '::error::%s\n' "$*" >&2
  exit 1
}

read_single() {
  local description=$1
  local file=$2
  local expression=$3
  local -a matches=()

  mapfile -t matches < <(sed -nE "$expression" "$file")
  ((${#matches[@]} == 1)) || fail "Expected exactly one ${description} in ${file}; found ${#matches[@]}."
  printf '%s\n' "${matches[0]}"
}

case "${1:-}" in
  "")
    repo_root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
    ;;
  --root)
    (($# == 2)) || {
      usage >&2
      exit 2
    }
    repo_root=$(CDPATH='' cd -- "$2" && pwd)
    ;;
  --help|-h)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

for command in awk curl git helm sed; do
  command -v "$command" >/dev/null 2>&1 || fail "Required command not found: ${command}."
done

crd_file="$repo_root/apps/base/fission/kustomization.yaml"
release_file="$repo_root/apps/base/fission/release.yaml"
workflow_file="$repo_root/.github/workflows/deploy-functions.yml"
devcontainer_file="$repo_root/.devcontainer/devcontainer.json"

for file in "$crd_file" "$release_file" "$workflow_file" "$devcontainer_file"; do
  test -f "$file" || fail "Required Fission pin file is missing: ${file}."
done

crd_metadata=$(read_single \
  'Fission CRD version and Git object' \
  "$crd_file" \
  's/^[[:space:]]*# Fission v([0-9]+\.[0-9]+\.[0-9]+) tag, resolved to immutable Git object ([0-9a-f]{40})\.$/\1 \2/p')
read -r crd_version crd_object <<<"$crd_metadata"
crd_url_object=$(read_single \
  'Fission CRD URL Git object' \
  "$crd_file" \
  's#^[[:space:]]*- https://github\.com/fission/fission/crds/v1\?ref=([0-9a-f]{40})$#\1#p')
chart_version=$(read_single \
  'Fission Helm chart version' \
  "$release_file" \
  's/^[[:space:]]*version: ([0-9]+\.[0-9]+\.[0-9]+)$/\1/p')
workflow_version=$(read_single \
  'Fission deployment CLI version' \
  "$workflow_file" \
  's/^  FISSION_VERSION: v([0-9]+\.[0-9]+\.[0-9]+)$/\1/p')
workflow_sha=$(read_single \
  'Fission deployment CLI SHA-256' \
  "$workflow_file" \
  's/^  FISSION_SHA256: ([0-9a-f]{64})$/\1/p')
devcontainer_version=$(read_single \
  'Fission Dev Container CLI version' \
  "$devcontainer_file" \
  '/renovate: datasource=custom\.fission-releases depName=fission\/fission versioning=semver-coerced/{n;s/^[[:space:]]*"version": "([0-9]+\.[0-9]+\.[0-9]+)"[,]?$/\1/p;}')

for value in "$crd_version" "$chart_version" "$workflow_version" "$devcontainer_version"; do
  [[ "$value" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "Invalid Fission version: ${value}."
done
[[ "$crd_object" == "$crd_url_object" ]] || fail 'The Fission CRD comment and URL pin different Git objects.'
[[ "$workflow_sha" =~ ^[0-9a-f]{64}$ ]] || fail 'The Fission deployment CLI checksum is not a SHA-256 value.'

for pin_name in crd chart workflow devcontainer; do
  declare -n pin_version="${pin_name}_version"
  [[ "$pin_version" == "$chart_version" ]] ||
    fail "Fission ${pin_name} pin (${pin_version}) does not match the Helm chart version (${chart_version})."
done

fission_git_remote=${FISSION_GIT_REMOTE:-https://github.com/fission/fission.git}
fission_release_download_url=${FISSION_RELEASE_DOWNLOAD_URL:-https://github.com/fission/fission/releases/download}
fission_chart_repository=${FISSION_CHART_REPOSITORY:-https://fission.github.io/fission-charts}

mapfile -t tag_objects < <(
  git ls-remote --refs "$fission_git_remote" "refs/tags/v${chart_version}" | awk '{print $1}'
)
((${#tag_objects[@]} == 1)) || fail "Expected one upstream Fission tag for v${chart_version}; found ${#tag_objects[@]}."
[[ "${tag_objects[0]}" == "$crd_object" ]] ||
  fail "Fission CRD Git object (${crd_object}) does not match tag v${chart_version} (${tag_objects[0]})."

cli_asset="fission-v${chart_version}-linux-amd64"
upstream_sha=$(curl -fsSL "${fission_release_download_url}/v${chart_version}/checksums.txt" | \
  awk -v asset="$cli_asset" '$2 == asset { print $1 }')
[[ "$upstream_sha" =~ ^[0-9a-f]{64}$ ]] ||
  fail "No SHA-256 was found for ${cli_asset} in the Fission v${chart_version} checksums."
[[ "$upstream_sha" == "$workflow_sha" ]] ||
  fail "Fission deployment CLI checksum does not match the published v${chart_version} checksum."

chart_metadata=$(helm show chart fission-all --repo "$fission_chart_repository" --version "$chart_version")
chart_app_version=$(printf '%s\n' "$chart_metadata" | sed -nE 's/^appVersion: v([0-9]+\.[0-9]+\.[0-9]+)$/\1/p')
[[ "$chart_app_version" == "$chart_version" ]] ||
  fail "Fission chart fission-all@${chart_version} declares appVersion v${chart_app_version:-missing}."

printf 'Fission platform pins are aligned to v%s.\n' "$chart_version"
