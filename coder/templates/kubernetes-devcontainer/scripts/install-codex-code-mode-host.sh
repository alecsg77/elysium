#!/usr/bin/env bash
set -euo pipefail

for command in awk curl install mkdir mktemp mv rm sha256sum tar uname; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Cannot install codex-code-mode-host: required command '$command' is unavailable." >&2
    exit 1
  fi
done

codex_bin="$HOME/.local/bin/codex"
if [[ ! -x "$codex_bin" ]]; then
  echo "Cannot install codex-code-mode-host: Codex CLI is not executable at $codex_bin." >&2
  exit 1
fi

codex_version_output="$($codex_bin --version)"
codex_version="$(awk '$1 == "codex-cli" && NF == 2 { print $2; exit }' <<<"$codex_version_output")"
if [[ ! "$codex_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]]; then
  echo "Cannot install codex-code-mode-host: unexpected Codex CLI version output '$codex_version_output'." >&2
  exit 1
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Cannot install codex-code-mode-host: only Linux workspaces are supported." >&2
  exit 1
fi

case "$(uname -m)" in
  x86_64 | amd64)
    target="x86_64-unknown-linux-musl"
    ;;
  aarch64 | arm64)
    target="aarch64-unknown-linux-musl"
    ;;
  *)
    echo "Cannot install codex-code-mode-host: unsupported architecture '$(uname -m)'." >&2
    exit 1
    ;;
esac

asset="codex-package-$target.tar.gz"
release_url="https://github.com/openai/codex/releases/download/rust-v$codex_version"
temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/codex-code-mode-host.XXXXXX")"
staged_path=""

cleanup() {
  if [[ -n "$staged_path" ]]; then
    rm -f -- "$staged_path"
  fi
  rm -rf -- "$temp_dir"
}
trap cleanup EXIT

archive="$temp_dir/$asset"
checksum_manifest="$temp_dir/codex-package_SHA256SUMS"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
  "$release_url/codex-package_SHA256SUMS" \
  --output "$checksum_manifest"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
  "$release_url/$asset" \
  --output "$archive"

if ! expected_digest="$(awk -v asset="$asset" '
  $2 == asset && length($1) == 64 && $1 !~ /[^0-9a-fA-F]/ {
    print tolower($1)
    found = 1
    exit
  }
  END { if (!found) exit 1 }
' "$checksum_manifest")"; then
  echo "Cannot install codex-code-mode-host: no valid digest for $asset in the official checksum manifest." >&2
  exit 1
fi

actual_digest="$(sha256sum "$archive" | awk '{ print tolower($1) }')"
if [[ "$actual_digest" != "$expected_digest" ]]; then
  echo "Cannot install codex-code-mode-host: checksum verification failed for $asset." >&2
  exit 1
fi

extract_dir="$temp_dir/extract"
mkdir -p "$extract_dir"
tar -xzf "$archive" -C "$extract_dir" bin/codex-code-mode-host
host_source="$extract_dir/bin/codex-code-mode-host"
if [[ ! -f "$host_source" ]]; then
  echo "Cannot install codex-code-mode-host: verified package $asset does not contain the host binary." >&2
  exit 1
fi

install_dir="$HOME/.local/bin"
install -d -m 0755 "$install_dir"
staged_path="$install_dir/.codex-code-mode-host.$$.tmp"
install -m 0755 "$host_source" "$staged_path"
mv -f -- "$staged_path" "$install_dir/codex-code-mode-host"
staged_path=""

if [[ ! -x "$install_dir/codex-code-mode-host" ]]; then
  echo "Cannot install codex-code-mode-host: installed file is not executable." >&2
  exit 1
fi

echo "Installed verified codex-code-mode-host $codex_version for $target."
