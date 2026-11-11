# Orca Hub image

Checksum-pinned Orca 1.4.248 for Linux amd64, with Coder CLI 2.39.0 and OpenSSH.
The Electron runtime is selected explicitly because this Orca release's Node
runtime cannot manage SSH targets. Xvfb provides the virtual display. The
extracted AppImage launcher automatically handles unavailable user namespaces;
this container does not provide Chromium sandbox isolation between agent tasks.

Build with `docker build -t elysium/orca-hub:1.4.248 images/orca-hub`.
See the [image catalog](../README.md) for build, publication, and update conventions.
No runtime profile or provider credentials are baked into the image.

To update Orca, change `ORCA_VERSION` and the matching AppImage `ORCA_SHA256` in
`Dockerfile`, then update `VERSION`. Coder CLI is pinned by its source image tag.
Repeat the SSH and client acceptance checks after an upstream update: the Electron
runtime requirement is specific to the currently pinned Orca release.

Mount the complete `/home/coder` and set `ORCA_PAIRING_ADDRESS` to a private
address reachable by the clients. Include the published port in a full `ws://`
or `wss://` URL when a proxy or port mapping changes it. The initial pairing is runtime-scoped for desktop/browser clients. Set
`ORCA_MOBILE_PAIRING=1` for a mobile-scoped link on a subsequent start; existing
paired clients retain their grants. Access links and QR codes in startup logs are credentials. Keep them private.
Electron without a desktop keyring reports that locally stored provider secrets
are unencrypted; protect the home volume. Prefer agent/provider credentials on
the workers and retain only Coder access on the hub.

The Kubernetes catalog unit is intentionally not selected by any cluster overlay.
See [pilot runbook](../../docs/runbooks/orca-pilot.md) for setup and acceptance.
