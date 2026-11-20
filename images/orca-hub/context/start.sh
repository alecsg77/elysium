#!/bin/sh
set -eu

: "${ORCA_PAIRING_ADDRESS:?Set the private address reachable by your Orca clients}"
mkdir -p "$ORCA_USER_DATA_PATH"
exec orca-ide serve --bind 0.0.0.0 --port 6768 \
  --pairing-address "$ORCA_PAIRING_ADDRESS" --no-pairing "$@"
