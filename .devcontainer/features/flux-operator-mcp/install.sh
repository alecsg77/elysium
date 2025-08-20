#!/bin/sh
set -e

readonly FLUXOPERATORMCP_VERSION="${VERSION:-"latest"}"

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
    if [ "${FLUXOPERATORMCP_VERSION}" != "latest" ] ; then
        CHECKSUMS_URL="https://github.com/controlplaneio-fluxcd/flux-operator/releases/download/v${FLUXOPERATORMCP_VERSION#[vV]}/checksums.txt"
        ASSET_URL="https://github.com/controlplaneio-fluxcd/flux-operator/releases/download/v${FLUXOPERATORMCP_VERSION#[vV]}/flux-operator-mcp_v${FLUXOPERATORMCP_VERSION#[vV]}_linux_${ARCH}.tar.gz"
    else
        local RELEASES_RESPONSE="$(wget -qO- --tries=3 https://api.github.com/repos/controlplaneio-fluxcd/flux-operator/releases)"
        CHECKSUMS_URL="$(echo "${RELEASES_RESPONSE}" | grep "browser_download_url.*checksums.txt" | head -n 1 | cut -d '"' -f 4)"
        ASSET_URL="$(echo "${RELEASES_RESPONSE}" | grep "browser_download_url.*flux-operator-mcp.*linux_${ARCH}" | head -n 1 | cut -d '"' -f 4)"
    fi

    echo "Installing flux-operator-mcp ${FLUXOPERATORMCP_VERSION} for ${ARCH} ..."

    echo "Downloading checksums ${CHECKSUMS_URL} ..."
    wget --no-verbose -O /tmp/checksums.txt "${CHECKSUMS_URL}"
    local SHA="$(grep "flux-operator-mcp_.*linux_${ARCH}" /tmp/checksums.txt | cut -d ' ' -f 1)"

    echo "Downloading ${ASSET_URL} ..."
    wget --no-verbose -O /tmp/flux-operator-mcp.tar.gz "${ASSET_URL}"

    echo "Verifying checksum ${SHA} ..."
    echo "${SHA}  /tmp/flux-operator-mcp.tar.gz" | sha256sum -c -

    # Move binary to a location in PATH
    mkdir -p /usr/local/bin
    tar -xzf /tmp/flux-operator-mcp.tar.gz -C /tmp/
    mv /tmp/flux-operator-mcp /usr/local/bin/
    chmod +x /usr/local/bin/flux-operator-mcp

    echo "flux-operator-mcp ${FLUXOPERATORMCP_VERSION} for ${ARCH} installed at $(command -v flux-operator-mcp)."
}

main "$@"