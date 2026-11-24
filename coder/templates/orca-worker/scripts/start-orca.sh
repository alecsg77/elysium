#!/usr/bin/env bash
set -euo pipefail
umask 077

# Renovate updates the release version and its SHA-256 together.
version=1.4.273
deb_sha=8e3a3497c208bc0d53c0cfc3ce6fef7f1cf659361246eee4d3da0ccf73eb4d15
asset="orca-ide_${version}_amd64.deb"
release="https://github.com/stablyai/orca/releases/download/v$version"
state="$HOME/.local/share/orca"
install_dir="$state/desktop-$version"
cli="$install_dir/opt/Orca/resources/bin/orca-ide"
project=/workspaces/project

export PATH="$HOME/.local/bin:$PATH"
export ORCA_USER_DATA_PATH="${ORCA_USER_DATA_PATH:-$state/profile}"
mkdir -p "$state" "$ORCA_USER_DATA_PATH" "$HOME/.local/bin"

if [[ ! -x "$cli" ]]; then
  staging=$(mktemp -d "$state/install.XXXXXX")
  trap 'rm -rf -- "$staging"' EXIT
  (
    cd "$staging"
    curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
      --retry 2 --connect-timeout 15 --max-time 300 "$release/$asset" -o "$asset"
    printf '%s  %s\n' "$deb_sha" "$asset" | sha256sum --check --strict
    dpkg-deb -x "$asset" package
    test -x package/opt/Orca/resources/bin/orca-ide
    mv -T package "$install_dir"
  )
fi

ln -sfn "$cli" "$HOME/.local/bin/orca-ide"
cd "$project"
ready() {
  curl --fail --silent --max-time 2 http://127.0.0.1:6768/ >/dev/null
}
if ! ready; then
  # Native clients reach the runtime through a private tunnel.
  ORCA_SERVE_RUNTIME=orcad nohup "$cli" serve --bind 0.0.0.0 --port 6768 --refuse-public --no-pairing \
    </dev/null >"$state/server.log" 2>&1 &
  server_pid=$!
  printf '%s\n' "$server_pid" >/tmp/coder-orca-serve.pid
  for ((attempt = 0; attempt < 30; attempt++)); do
    if ready; then break; fi
    if ! kill -0 "$server_pid" 2>/dev/null; then break; fi
    sleep 1
  done
  if ! ready; then
    echo "Orca Web did not respond on port 6768. Inspect $state/server.log." >&2
    exit 1
  fi
fi

"$cli" repo add --path "$project" --kind git >/dev/null
printf '%s\n' "Orca $version is ready."
