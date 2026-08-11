#!/bin/sh
# Rotate the tsidp OIDC client credentials consumed by Flux Web and Headlamp.
# Secrets are read from the terminal without echo, held in a mode-0700 temporary
# directory only long enough to seal them, then removed by the exit trap.
set -eu

usage() {
  cat <<'EOF'
Usage: sh scripts/rotate-oidc-sealed-secrets.sh [--dry-run]

Interactively update the OIDC credentials for Flux Web and Headlamp. Every
prompt is optional: press Enter to preserve that encrypted value. The script
uses kubeseal --merge-into, so it updates only supplied keys and never needs to
decrypt the existing SealedSecrets. A Headlamp credential change also regenerates
an opaque rollout token so its Pod restarts with the new environment. --dry-run
verifies sealing and discards any changes instead of replacing repository files.
EOF
}

case "${1:-}" in
  "")
    dry_run=false
    ;;
  --dry-run)
    dry_run=true
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

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

for command in kubectl kubeseal mktemp openssl; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'Required command not found: %s\n' "$command" >&2
    exit 1
  }
done

certificate=etc/certs/pub-sealed-secrets.pem
test -r "$certificate" || {
  printf 'Sealed Secrets public certificate is not readable: %s\n' "$certificate" >&2
  exit 1
}

flux_output=infrastructure/controllers/flux-operator/flux-web-client-sealed-secret.yaml
headlamp_output=monitoring/controllers/headlamp/headlamp-oidc-sealed-secret.yaml
for output in "$flux_output" "$headlamp_output"; do
  test -f "$output" || {
    printf 'Expected SealedSecret is missing: %s\n' "$output" >&2
    exit 1
  }
done

tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/rotate-oidc-sealed-secrets.XXXXXX")
chmod 700 "$tmpdir"

cleanup() {
  stty echo </dev/tty 2>/dev/null || :
  rm -rf -- "$tmpdir"
}
trap cleanup EXIT HUP INT TERM

read_optional_value() {
  prompt=$1
  printf '%s' "$prompt" >/dev/tty
  IFS= read -r value </dev/tty || exit 1
  printf '%s' "$value"
}

read_optional_secret() {
  prompt=$1
  printf '%s' "$prompt" >/dev/tty
  stty -echo </dev/tty
  if ! IFS= read -r value </dev/tty; then
    stty echo </dev/tty
    exit 1
  fi
  stty echo </dev/tty
  printf '\n' >/dev/tty
  printf '%s' "$value"
}

store_if_supplied() {
  value=$1
  path=$2
  test -n "$value" || return 0
  printf '%s' "$value" >"$path"
}

issuer_url=$(read_optional_value 'tsidp OIDC issuer URL [Enter to keep current]: ')
flux_client_id=$(read_optional_value 'Flux Web OIDC client ID [Enter to keep current]: ')
flux_client_secret=$(read_optional_secret 'Flux Web OIDC client secret [Enter to keep current; input hidden]: ')
headlamp_client_id=$(read_optional_value 'Headlamp OIDC client ID [Enter to keep current]: ')
headlamp_client_secret=$(read_optional_secret 'Headlamp OIDC client secret [Enter to keep current; input hidden]: ')

store_if_supplied "$issuer_url" "$tmpdir/issuer-url"
store_if_supplied "$flux_client_id" "$tmpdir/flux-client-id"
store_if_supplied "$flux_client_secret" "$tmpdir/flux-client-secret"
store_if_supplied "$headlamp_client_id" "$tmpdir/headlamp-client-id"
store_if_supplied "$headlamp_client_secret" "$tmpdir/headlamp-client-secret"
unset issuer_url flux_client_id flux_client_secret headlamp_client_id headlamp_client_secret

merge_flux_web() {
  target=$1
  set -- kubectl create secret generic flux-web-client \
    --namespace flux-system \
    --dry-run=client \
    --output yaml
  test ! -f "$tmpdir/flux-client-id" || set -- "$@" --from-file=client-id="$tmpdir/flux-client-id"
  test ! -f "$tmpdir/flux-client-secret" || set -- "$@" --from-file=client-secret="$tmpdir/flux-client-secret"
  test ! -f "$tmpdir/issuer-url" || set -- "$@" --from-file=issuer-url="$tmpdir/issuer-url"
  "$@" | kubeseal --cert "$certificate" --format yaml --merge-into "$target"
}

merge_headlamp() {
  target=$1
  set -- kubectl create secret generic headlamp-oidc \
    --namespace kube-system \
    --dry-run=client \
    --output yaml
  test ! -f "$tmpdir/headlamp-client-id" || set -- "$@" --from-file=OIDC_CLIENT_ID="$tmpdir/headlamp-client-id"
  test ! -f "$tmpdir/headlamp-client-secret" || set -- "$@" --from-file=OIDC_CLIENT_SECRET="$tmpdir/headlamp-client-secret"
  test ! -f "$tmpdir/issuer-url" || set -- "$@" --from-file=OIDC_ISSUER_URL="$tmpdir/issuer-url"
  test ! -f "$tmpdir/headlamp-rollout-token" || set -- "$@" --from-file=HEADLAMP_ROLLOUT_TOKEN="$tmpdir/headlamp-rollout-token"
  "$@" | kubeseal --cert "$certificate" --format yaml --merge-into "$target"
}

flux_updated=false
headlamp_updated=false

if test -f "$tmpdir/flux-client-id" || test -f "$tmpdir/flux-client-secret" || test -f "$tmpdir/issuer-url"; then
  cp "$flux_output" "$tmpdir/flux-web-client-sealed-secret.yaml"
  merge_flux_web "$tmpdir/flux-web-client-sealed-secret.yaml"
  flux_updated=true
fi

if test -f "$tmpdir/headlamp-client-id" || test -f "$tmpdir/headlamp-client-secret" || test -f "$tmpdir/issuer-url"; then
  # Environment variables from a Secret are fixed when a Pod starts. Rotate this
  # opaque token with Headlamp OIDC values so helm-controller upgrades the chart
  # and the pod-template annotation triggers a rollout.
  openssl rand -hex 32 >"$tmpdir/headlamp-rollout-token"
  cp "$headlamp_output" "$tmpdir/headlamp-oidc-sealed-secret.yaml"
  merge_headlamp "$tmpdir/headlamp-oidc-sealed-secret.yaml"
  headlamp_updated=true
fi

if ! "$flux_updated" && ! "$headlamp_updated"; then
  printf '%s\n' 'No values were supplied; no SealedSecrets were changed.'
  exit 0
fi

if "$dry_run"; then
  printf '%s\n' 'Sealed supplied OIDC values successfully; dry-run discarded the output.'
  exit 0
fi

if "$flux_updated"; then
  install -m 0644 "$tmpdir/flux-web-client-sealed-secret.yaml" "$flux_output"
fi
if "$headlamp_updated"; then
  install -m 0644 "$tmpdir/headlamp-oidc-sealed-secret.yaml" "$headlamp_output"
fi

printf '%s\n' 'Updated the supplied OIDC values in the relevant SealedSecrets.'
if test -f "$tmpdir/headlamp-client-id"; then
  printf '%s\n' 'Headlamp client ID changed: update the control-plane k3s OIDC audience before reconciling Headlamp.'
fi
