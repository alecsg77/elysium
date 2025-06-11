#!/bin/sh
set -e

readonly FISSION_VERSION="${VERSION:-"latest"}"

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
    preflight

    local ARCH="$(uname -m)"
    case "${ARCH}" in
        "aarch64") ARCH="arm64" ;;
        "x86_64") ARCH="amd64" ;;
        *) echo "The current architecture (${ARCH}) is not supported."; exit 1 ;;
    esac

    # Get the latest version from GitHub if needed
    if [ "${FISSION_VERSION}" != "latest" ] ; then
        CHECKSUMS_URL="https://github.com/fission/fission/releases/download/v${FISSION_VERSION#[vV]}/checksums.txt"
        BINARY_URL="https://github.com/fission/fission/releases/download/v${FISSION_VERSION#[vV]}/fission-v${FISSION_VERSION#[vV]}-linux-${ARCH}"
    else
        local RELEASES_RESPONSE="$(wget -qO- --tries=3 https://api.github.com/repos/fission/fission/releases)"
        CHECKSUMS_URL="$(echo "${RELEASES_RESPONSE}" | grep "browser_download_url.*checksums.txt" | head -n 1 | cut -d '"' -f 4)"
        BINARY_URL="$(echo "${RELEASES_RESPONSE}" | grep "browser_download_url.*linux-${ARCH}" | head -n 1 | cut -d '"' -f 4)"
    fi

    echo "Installing fission ${FISSION_VERSION} for ${ARCH} ..."

    echo "Downloading checksums ${CHECKSUMS_URL} ..."
    wget --no-verbose -O /tmp/checksums.txt "${CHECKSUMS_URL}"
    local SHA="$(grep linux-${ARCH} /tmp/checksums.txt | cut -d ' ' -f 1)"

    echo "Downloading ${BINARY_URL} ..."
    wget --no-verbose -O /tmp/fission "${BINARY_URL}"

    echo "Verifying checksum ${SHA} ..."
    echo "${SHA}  /tmp/fission" | sha256sum -c -

    # Move binary to a location in PATH
    mkdir -p /usr/local/bin
    mv /tmp/fission /usr/local/bin/
    chmod +x /usr/local/bin/fission

    echo "fission ${FISSION_VERSION} for ${ARCH} installed at $(command -v fission)."
}

main "$@"