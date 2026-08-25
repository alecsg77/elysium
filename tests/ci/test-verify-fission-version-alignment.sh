#!/usr/bin/env bash
set -euo pipefail

repo_root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
checker="$repo_root/scripts/ci/verify-fission-version-alignment.sh"
fixture=$(mktemp -d)
trap 'rm -rf -- "$fixture"' EXIT

mkdir -p \
  "$fixture/bin" \
  "$fixture/repo/apps/base/fission" \
  "$fixture/repo/.github/workflows" \
  "$fixture/repo/.devcontainer"

cat >"$fixture/repo/apps/base/fission/kustomization.yaml" <<'EOF'
resources:
  # renovate: datasource=custom.fission-git-tags depName=fission/fission versioning=semver-coerced
  # Fission v1.27.0 tag, resolved to immutable Git object 1e1401cdecd7281129482e681580b4bdc0741770.
  - https://github.com/fission/fission/crds/v1?ref=1e1401cdecd7281129482e681580b4bdc0741770
EOF
cat >"$fixture/repo/apps/base/fission/release.yaml" <<'EOF'
spec:
  chart:
    spec:
      chart: fission-all
      # renovate: datasource=custom.fission-releases depName=fission/fission versioning=semver-coerced
      version: 1.27.0
EOF
cat >"$fixture/repo/.github/workflows/deploy-functions.yml" <<'EOF'
env:
  # renovate: datasource=custom.fission-releases depName=fission/fission versioning=semver-coerced
  FISSION_VERSION: v1.27.0
  FISSION_SHA256: 69eb82c53945ae8bdd5842933a88459b7004fe8eb2f0ab1c3de0a814e04ca9e9
EOF
cat >"$fixture/repo/.devcontainer/devcontainer.json" <<'EOF'
{
  "features": {
    "./features/fission-cli": {
      // renovate: datasource=custom.fission-releases depName=fission/fission versioning=semver-coerced
      "version": "1.27.0"
    }
  }
}
EOF
cat >"$fixture/bin/git" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\t%s\n' \
  '1e1401cdecd7281129482e681580b4bdc0741770' \
  'refs/tags/v1.27.0'
EOF
cat >"$fixture/bin/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s  %s\n' \
  '69eb82c53945ae8bdd5842933a88459b7004fe8eb2f0ab1c3de0a814e04ca9e9' \
  'fission-v1.27.0-linux-amd64'
EOF
cat >"$fixture/bin/helm" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'appVersion: v1.27.0'
EOF
chmod +x "$fixture/bin/git" "$fixture/bin/curl" "$fixture/bin/helm"

PATH="$fixture/bin:$PATH" bash "$checker" --root "$fixture/repo" >"$fixture/success.out"
grep -qx 'Fission platform pins are aligned to v1.27.0.' "$fixture/success.out"

sed -i \
  's/^  FISSION_SHA256: .*/  FISSION_SHA256: 0000000000000000000000000000000000000000000000000000000000000000/' \
  "$fixture/repo/.github/workflows/deploy-functions.yml"
if PATH="$fixture/bin:$PATH" bash "$checker" --root "$fixture/repo" >"$fixture/failure.out" 2>&1; then
  printf '%s\n' 'Expected the checker to reject an invalid Fission CLI checksum.' >&2
  exit 1
fi
grep -Fqx '::error::Fission deployment CLI checksum does not match the published v1.27.0 checksum.' \
  "$fixture/failure.out"

printf '%s\n' 'verify-fission-version-alignment tests passed.'
