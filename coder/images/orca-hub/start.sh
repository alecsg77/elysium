#!/bin/sh
set -eu

: "${ORCA_PAIRING_ADDRESS:?Set the private address reachable by your Orca clients}"
mkdir -p "$ORCA_USER_DATA_PATH"
if [ "${ORCA_MOBILE_PAIRING:-0}" = 1 ]; then
  set -- --mobile-pairing "$@"
fi
exec xvfb-run -a --server-args='-screen 0 1280x800x24 -nolisten tcp' \
  orca-ide serve --port 6768 --pairing-address "$ORCA_PAIRING_ADDRESS" \
  --json "$@"
