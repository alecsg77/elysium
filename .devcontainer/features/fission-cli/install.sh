#!/bin/sh
set -e

VERSION="${VERSION:-"latest"}"
ARCHITECTURE="${ARCHITECTURE:-"amd64"}"

echo "Activating feature 'fission-cli'"
echo "Version: ${VERSION}"
echo "Architecture: ${ARCHITECTURE}"

# Detect OS
case "$(uname -s)" in
    Linux*)     OS=linux;;
    Darwin*)    OS=darwin;;
    *)          echo "Unsupported OS. Use Linux or Mac."; exit 1;;
esac

# Create a temporary directory for downloads
TEMP_DIR=$(mktemp -d)
cd "${TEMP_DIR}"

# Get the latest version from GitHub if needed
if [ "${VERSION}" = "latest" ]; then
    echo "Determining the latest Fission CLI release..."
    VERSION=$(curl -s https://api.github.com/repos/fission/fission/releases/latest | grep -oP '"name": "\K(.*)(?=")')
    if [ -z "${VERSION}" ]; then
        echo "Failed to determine latest version. Please specify a version explicitly."
        exit 1
    fi
    echo "Latest version: ${VERSION}"
fi

# Download the appropriate binary
BINARY_URL="https://github.com/fission/fission/releases/download/${VERSION}/fission-${VERSION}-${OS}-${ARCHITECTURE}"
echo "Downloading Fission CLI from ${BINARY_URL}"

# Download binary
curl -Lo fission "${BINARY_URL}"

# Make binary executable
chmod +x fission

# Move binary to a location in PATH
mkdir -p /usr/local/bin
mv fission /usr/local/bin/

# Clean up
cd -
rm -rf "${TEMP_DIR}"