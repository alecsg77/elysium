#!/usr/bin/env bash
set -euo pipefail
umask 077

# Renovate updates the release version and its SHA-256 together.
version=1.4.266
server_sha=a45ca96d3c781b78231d5af2cd534149607d05df9c5b9fdcd545fe6c87ee88b5
asset=orca-server-linux-x64.tar.gz
release="https://github.com/stablyai/orca/releases/download/v$version"
state="$HOME/.local/share/orca"
install_dir="$state/server-$version"
cli="$install_dir/bin/orca-ide"
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
    printf '%s  %s\n' "$server_sha" "$asset" | sha256sum --check --strict
    mkdir server
    tar -xzf "$asset" --strip-components=1 -C server
    test -x server/bin/orca-ide
    mv -T server "$install_dir"
  )
fi

ln -sfn "$cli" "$HOME/.local/bin/orca-ide"
cd "$project"
ready() {
  (true >/dev/tcp/127.0.0.1/6768) 2>/dev/null
}
if ! ready; then
  # Native clients reach the runtime through a private tunnel.
  nohup "$cli" serve --bind 0.0.0.0 --port 6768 --refuse-public --no-pairing \
    </dev/null >"$state/server.log" 2>&1 &
  server_pid=$!
  for ((attempt = 0; attempt < 30; attempt++)); do
    if ready; then break; fi
    if ! kill -0 "$server_pid" 2>/dev/null; then break; fi
    sleep 1
  done
  if ! ready; then
    echo "Orca did not open port 6768. Inspect $state/server.log." >&2
    exit 1
  fi
fi

"$cli" repo add --path "$project" --kind git >/dev/null
printf '%s\n' "Orca $version is ready."
