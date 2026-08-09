#!/usr/bin/env bash
# Creates a strict, namespace-bound SealedSecret for the Headlamp OIDC client.
# Run from the repository root: bash scripts/create-headlamp-oidc-sealed-secret.sh

set -Eeuo pipefail

readonly cert_path="etc/certs/pub-sealed-secrets.pem"
readonly output_path="monitoring/controllers/headlamp/headlamp-oidc-sealed-secret.yaml"
temp_dir=""

cleanup() {
  local status=$?

  [[ -z "$temp_dir" ]] || rm -rf -- "$temp_dir"

  if (( status != 0 )); then
    rm -f -- "$output_path"
    printf '\nFailed before creating a valid SealedSecret (exit %d).\n' "$status" >&2
    printf 'The destination file was removed. Read the error above; do not share credentials.\n' >&2
  fi
}
trap cleanup EXIT

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'Required command is unavailable: %s\n' "$1" >&2
    return 1
  }
}

require_command kubectl
require_command kubeseal
[[ -r "$cert_path" ]] || {
  printf 'Sealed Secrets public certificate is missing or unreadable: %s\n' "$cert_path" >&2
  exit 1
}
[[ ! -e "$output_path" ]] || {
  printf 'Refusing to overwrite existing file: %s\n' "$output_path" >&2
  exit 1
}

read -r -p 'tsidp issuer URL: ' issuer_url
read -r -p 'Headlamp OIDC client ID: ' client_id
read -r -s -p 'Headlamp OIDC client secret: ' client_secret
printf '\n'

[[ -n "$issuer_url" ]] || { printf 'Issuer URL must not be empty.\n' >&2; exit 1; }
[[ -n "$client_id" ]] || { printf 'Client ID must not be empty.\n' >&2; exit 1; }
[[ -n "$client_secret" ]] || { printf 'Client secret must not be empty.\n' >&2; exit 1; }

temp_dir="$(mktemp -d)"
printf '%s' "$client_id" >"$temp_dir/HEADLAMP_CONFIG_OIDC_CLIENT_ID"
printf '%s' "$client_secret" >"$temp_dir/HEADLAMP_CONFIG_OIDC_CLIENT_SECRET"
printf '%s' "$issuer_url" >"$temp_dir/HEADLAMP_CONFIG_OIDC_IDP_ISSUER_URL"
printf '%s' 'profile,email' >"$temp_dir/HEADLAMP_CONFIG_OIDC_SCOPES"
unset client_secret

kubectl create secret generic headlamp-oidc \
  --namespace kube-system \
  --from-file=HEADLAMP_CONFIG_OIDC_CLIENT_ID="$temp_dir/HEADLAMP_CONFIG_OIDC_CLIENT_ID" \
  --from-file=HEADLAMP_CONFIG_OIDC_CLIENT_SECRET="$temp_dir/HEADLAMP_CONFIG_OIDC_CLIENT_SECRET" \
  --from-file=HEADLAMP_CONFIG_OIDC_IDP_ISSUER_URL="$temp_dir/HEADLAMP_CONFIG_OIDC_IDP_ISSUER_URL" \
  --from-file=HEADLAMP_CONFIG_OIDC_SCOPES="$temp_dir/HEADLAMP_CONFIG_OIDC_SCOPES" \
  --dry-run=client \
  --output yaml \
  | kubeseal --cert "$cert_path" --format yaml --scope strict \
  >"$output_path"

[[ -s "$output_path" ]] || {
  printf 'kubeseal produced an empty file.\n' >&2
  rm -f -- "$output_path"
  exit 1
}

printf 'Created %s\n' "$output_path"
