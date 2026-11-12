#!/usr/bin/env bash
set -euo pipefail

version=1.19.5
digest=17c200fd4b2289954cc01552559f9b6d03ec157b2ddfb5eb54144f491656333d
binary="$HOME/.local/bin/opencode"
if [[ -x "$binary" ]] && [[ "$("$binary" --version)" == "$version" ]]; then
  exit 0
fi

temporary=$(mktemp -d)
trap 'rm -rf -- "$temporary"' EXIT
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
  "https://github.com/anomalyco/opencode/releases/download/v$version/opencode-linux-x64-baseline.tar.gz" \
  --output "$temporary/opencode.tar.gz"
printf '%s  %s\n' "$digest" "$temporary/opencode.tar.gz" | sha256sum --check --strict
tar -xzf "$temporary/opencode.tar.gz" -C "$temporary"
install -d -m 0755 "$HOME/.local/bin"
install -m 0755 "$temporary/opencode" "$binary"
"$binary" --version
