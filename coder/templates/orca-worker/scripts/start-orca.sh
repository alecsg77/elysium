#!/usr/bin/env bash
set -euo pipefail
umask 077

version=1.4.265
server_sha=eaba2039f351d47e2ddc5d1c1f0335df3ae81b5830565adc1bcba23fc7004d0c
appimage_sha=8a51a08e241899d86775ad33f3af3a9e114b9cb300b79de1e764c922a0337026
release="https://github.com/stablyai/orca/releases/download/v$version"
state="$HOME/.local/share/orca"
install_dir="$state/$version"
cli="$install_dir/bin/orca-ide"
project=/workspaces/project

export PATH="$HOME/.local/bin:$PATH"
export ORCA_USER_DATA_PATH="${ORCA_USER_DATA_PATH:-$state/profile}"
mkdir -p "$state" "$ORCA_USER_DATA_PATH" "$HOME/.local/bin"

download() {
  local asset=$1 digest=$2
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    --retry 2 --connect-timeout 15 --max-time 300 "$release/$asset" -o "$asset"
  printf '%s  %s\n' "$digest" "$asset" | sha256sum --check --strict
}

if [[ ! -x "$cli" || ! -s "$install_dir/out/renderer/.orca-web-client-files.json" ]]; then
  staging=$(mktemp -d "$state/install.XXXXXX")
  trap 'rm -rf -- "$staging"' EXIT
  (
    cd "$staging"
    download orca-server-linux-x64.tar.gz "$server_sha"
    download orca-linux.AppImage "$appimage_sha"
    mkdir server
    tar -xzf orca-server-linux-x64.tar.gz --strip-components=1 -C server
    chmod 0700 orca-linux.AppImage
    ./orca-linux.AppImage --appimage-extract >/dev/null
    # The standalone launcher discovers the renderer and its asset allowlist here.
    renderer=squashfs-root/resources/app.asar.unpacked/out/renderer
    test -s "$renderer/web-index.html"
    test -s "$renderer/.orca-web-client-files.json"
    mv "$renderer" server/out/renderer
    mv -T server "$install_dir"
  )
fi

ln -sfn "$cli" "$HOME/.local/bin/orca-ide"
cd "$project"
ready() {
  curl --fail --silent --max-time 2 http://127.0.0.1:6768/ >/dev/null
}
if ! ready; then
  # Mobile pairing needs a network listener. Coder proxies loopback from inside
  # the pod, and native clients can reach it over a private Coder port forward.
  nohup "$cli" serve --bind 0.0.0.0 --port 6768 --refuse-public --no-pairing \
    </dev/null >"$state/server.log" 2>&1 &
  server_pid=$!
  for ((attempt = 0; attempt < 30; attempt++)); do
    if ready; then break; fi
    if ! kill -0 "$server_pid" 2>/dev/null; then break; fi
    sleep 1
  done
  if ! ready; then
    echo "Orca did not serve its web client. Inspect $state/server.log." >&2
    exit 1
  fi
fi

"$cli" repo add --path "$project" --kind git >/dev/null
printf '%s\n' "Orca $version is ready."
