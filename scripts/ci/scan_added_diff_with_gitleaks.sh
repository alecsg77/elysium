#!/usr/bin/env bash
# Scan only additions from a verified base-to-head diff with trusted Gitleaks.
# This helper is invoked from the trusted base checkout by pull_request_target.
set -euo pipefail

: "${BASE_SHA:?BASE_SHA is required}"
: "${HEAD_SHA:?HEAD_SHA is required}"
: "${PR_NUMBER:?PR_NUMBER is required}"
: "${GITLEAKS_VERSION:?GITLEAKS_VERSION is required}"
: "${GITLEAKS_SHA256:?GITLEAKS_SHA256 is required}"
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"

repo="${1:-.}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
scanner_dir="$RUNNER_TEMP/gitleaks"
archive="gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"

mkdir -p "$scanner_dir"
curl -fsSL -o "$scanner_dir/$archive" \
  "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${archive}"
echo "${GITLEAKS_SHA256}  ${scanner_dir}/${archive}" | sha256sum --check --strict
tar -xzf "$scanner_dir/$archive" -C "$scanner_dir"

# Fetch the proposed revision as Git data and verify it against the PR payload.
# The scanner only runs the checksum-verified binary; it never reads a Gitleaks
# configuration, executable, or workflow file from the proposed revision.
git -C "$repo" fetch --no-tags --depth=1 origin "$BASE_SHA"
git -C "$repo" fetch --no-tags --depth=1 origin "pull/${PR_NUMBER}/head:refs/remotes/origin/pr-head"
test "$(git -C "$repo" rev-parse "$BASE_SHA")" = "$BASE_SHA"
test "$(git -C "$repo" rev-parse refs/remotes/origin/pr-head)" = "$HEAD_SHA"

# The policy helper retains every added line except direct scalar ciphertext in
# an exact SealedSecret.spec.encryptedData location. It consumes trusted Git
# objects as data and writes no source content to workflow output. The --no-git
# file scan runs from scanner_dir, with config environment variables unset and
# its ignore-file lookup confined there. That forces built-in Gitleaks rules
# instead of PR-controlled .gitleaks.toml or .gitleaksignore content.
python3 "$script_dir/sealed_secret_ciphertext_policy.py" filter-added-diff \
  --repo "$repo" \
  --base-sha "$BASE_SHA" \
  --head-sha "$HEAD_SHA" \
  --output "$scanner_dir/proposed.diff"
(
  cd "$scanner_dir"
  env -u GITLEAKS_CONFIG -u GITLEAKS_CONFIG_TOML ./gitleaks detect \
    --no-git \
    --source "$scanner_dir/proposed.diff" \
    --gitleaks-ignore-path "$scanner_dir" \
    --no-banner \
    --no-color \
    --redact \
    --exit-code 1
)
