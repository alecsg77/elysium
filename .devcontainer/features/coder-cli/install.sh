#!/bin/sh
set -eu

readonly CODER_VERSION="${VERSION:-"latest"}"

# apt-get configuration
export DEBIAN_FRONTEND=noninteractive


preflight () {
    if command -v wget > /dev/null; then
        return
    fi

    if [ -e /etc/os-release ]; then
        . /etc/os-release
    fi

    case "${ID}" in
        'debian' | 'ubuntu')
            apt-get update
            apt-get install -y --no-install-recommends \
                wget \
                ca-certificates
        ;;
        'fedora')
            dnf -y install wget
        ;;
        *) echo "The ${ID} distribution is not supported."; exit 1 ;;
    esac
}

main () {
    if command -v coder > /dev/null; then
        echo "coder is already installed at $(command -v coder); skipping installation."
        return
    fi

    preflight

    local ARCH="$(uname -m)"
    case "${ARCH}" in
        "aarch64") ARCH="arm64" ;;
        "x86_64") ARCH="amd64" ;;
        *) echo "The current architecture (${ARCH}) is not supported."; exit 1 ;;
    esac

    # Get the latest release from GitHub if needed. Uses /releases/latest
    # (not /releases) so a pinned pre-release cannot ever be picked up by
    # accident, and both URLs below always come from the same release.
    if [ "${CODER_VERSION}" != "latest" ]; then
        local VER="${CODER_VERSION#[vV]}"
        local TAG="v${VER}"
        CHECKSUMS_URL="https://github.com/coder/coder/releases/download/${TAG}/coder_${VER}_checksums.txt"
        BINARY_URL="https://github.com/coder/coder/releases/download/${TAG}/coder_${VER}_linux_${ARCH}.tar.gz"
    else
        local RELEASE_RESPONSE="$(wget -qO- --tries=3 https://api.github.com/repos/coder/coder/releases/latest)"
        CHECKSUMS_URL="$(echo "${RELEASE_RESPONSE}" | grep 'browser_download_url.*checksums\.txt"' | head -n 1 | cut -d '"' -f 4)"
        BINARY_URL="$(echo "${RELEASE_RESPONSE}" | grep "browser_download_url.*linux_${ARCH}.tar.gz" | head -n 1 | cut -d '"' -f 4)"
    fi

    echo "Installing coder ${CODER_VERSION} for ${ARCH} ..."

    echo "Downloading checksums ${CHECKSUMS_URL} ..."
    wget --no-verbose -O /tmp/checksums.txt "${CHECKSUMS_URL}"
    local SHA="$(grep "linux_${ARCH}.tar.gz" /tmp/checksums.txt | cut -d ' ' -f 1)"

    echo "Downloading ${BINARY_URL} ..."
    wget --no-verbose -O /tmp/coder.tar.gz "${BINARY_URL}"

    echo "Verifying checksum ${SHA} ..."
    echo "${SHA}  /tmp/coder.tar.gz" | sha256sum -c -

    # Extract and move binary to a location in PATH
    mkdir -p /usr/local/bin
    tar -xzf /tmp/coder.tar.gz -C /tmp ./coder
    mv /tmp/coder /usr/local/bin/
    chmod +x /usr/local/bin/coder
    rm -f /tmp/coder.tar.gz /tmp/checksums.txt

    echo "coder ${CODER_VERSION} for ${ARCH} installed at $(command -v coder)."
}

main "$@"
