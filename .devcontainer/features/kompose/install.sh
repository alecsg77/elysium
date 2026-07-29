#!/bin/sh
set -e

readonly KOMPOSE_VERSION="${VERSION:-"1.34.0"}"

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

    # Get the latest release metadata from GitHub if needed. Uses
    # /releases/latest (a single release object, never a draft/prerelease)
    # rather than /releases (a list), so the checksum and binary URLs always
    # come from exactly the same release. URL patterns are anchored on the
    # trailing '"' so e.g. "kompose-linux-amd64" cannot also match
    # "kompose-linux-amd64.tar.gz" from the same release.
    if [ "${KOMPOSE_VERSION}" != "latest" ]; then
        local TAG="v${KOMPOSE_VERSION#[vV]}"
        CHECKSUMS_URL="https://github.com/kubernetes/kompose/releases/download/${TAG}/SHA256_SUM"
        BINARY_URL="https://github.com/kubernetes/kompose/releases/download/${TAG}/kompose-linux-${ARCH}"
    else
        local RELEASE_RESPONSE="$(wget -qO- --tries=3 https://api.github.com/repos/kubernetes/kompose/releases/latest)"
        CHECKSUMS_URL="$(echo "${RELEASE_RESPONSE}" | grep 'browser_download_url.*SHA256_SUM"' | head -n 1 | cut -d '"' -f 4)"
        BINARY_URL="$(echo "${RELEASE_RESPONSE}" | grep "browser_download_url.*kompose-linux-${ARCH}\"" | head -n 1 | cut -d '"' -f 4)"
    fi

    echo "Installing kompose ${KOMPOSE_VERSION} for ${ARCH} ..."

    echo "Downloading checksums ${CHECKSUMS_URL} ..."
    wget --no-verbose -O /tmp/checksums.txt "${CHECKSUMS_URL}"
    local SHA="$(grep " kompose-linux-${ARCH}\$" /tmp/checksums.txt | cut -d ' ' -f 1)"

    echo "Downloading ${BINARY_URL} ..."
    wget --no-verbose -O /tmp/kompose "${BINARY_URL}"

    echo "Verifying checksum ${SHA} ..."
    echo "${SHA}  /tmp/kompose" | sha256sum -c -

    # Move binary to a location in PATH
    mkdir -p /usr/local/bin
    mv /tmp/kompose /usr/local/bin/
    chmod +x /usr/local/bin/kompose

    echo "kompose ${KOMPOSE_VERSION} for ${ARCH} installed at $(command -v kompose)."
}

main "$@"
