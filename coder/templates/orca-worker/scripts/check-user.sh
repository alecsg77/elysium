#!/bin/sh
set -eu

user_record=$(getent passwd coder)
uid=$(printf '%s\n' "$user_record" | cut -d: -f3)
gid=$(printf '%s\n' "$user_record" | cut -d: -f4)
home=$(printf '%s\n' "$user_record" | cut -d: -f6)
if [ "$uid" != 1000 ] || [ "$gid" != 1000 ] || [ "$home" != /home/coder ]; then
  echo 'The project devcontainer must provide coder:1000:1000 with home /home/coder.' >&2
  exit 1
fi
if ! mountpoint -q /home/coder || ! mountpoint -q /workspaces; then
  echo 'Refusing to start without the persistent home and project mounts.' >&2
  exit 1
fi
printf '%s\n' 'TARGET_USER=coder' >> "$ENVBUILDER_ENV"
