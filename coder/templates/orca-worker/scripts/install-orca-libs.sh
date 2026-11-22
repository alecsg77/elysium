#!/bin/sh
set -eu

# The packaged CLI uses Electron in Node mode. APT installs its shared libraries.
apt-get -qq update
DEBIAN_FRONTEND=noninteractive apt-get -qq satisfy --no-install-recommends -y \
  'libgtk-3-0t64 | libgtk-3-0' \
  libnotify4 libnss3 libxss1 libxtst6 \
  'libatspi2.0-0t64 | libatspi2.0-0' \
  'libasound2t64 | libasound2' \
  libgbm1 libsecret-1-0
