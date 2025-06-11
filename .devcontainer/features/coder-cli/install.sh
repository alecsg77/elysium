#!/bin/sh
set -e

VERSION="${VERSION:-"latest"}"

echo "Activating feature 'coder-cli'"
echo "Version: ${VERSION}"

if [ "${VERSION}" = "latest" ]; then
    curl -L https://coder.com/install.sh | sh
else
    curl -L https://coder.com/install.sh | sh -s -- --version="${VERSION}"
fi
