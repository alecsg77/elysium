# Orca Hub image

This image installs the official checksum-pinned Orca Server 1.4.266
archive for Linux amd64. Coder CLI 2.39.0 and OpenSSH remain available for
administrative use. The hub runs its own Orca runtime.

Build with `docker build -t elysium/orca-hub:2.0.0 images/orca-hub/context`.
See the [image catalog](../README.md) for build and publication conventions.
To update Orca, change `ORCA_VERSION` and the matching server archive
`ORCA_SHA256` in `context/Dockerfile`, then increment `VERSION`.

Mount the complete `/home/coder` and set `ORCA_PAIRING_ADDRESS` to a private
address reachable by the clients. Include the published port in a full
`ws://` or `wss://` URL if a proxy or port mapping changes it.

The server starts with pairing offers disabled. Generate access links on demand
with `orca-ide pair --address <private-endpoint>` from an authorized shell inside
the container. Add `--mobile` for Orca Mobile. The links grant access to the
runtime and should be shared only with the intended client.

The [cluster rollout](../../docs/runbooks/orca-pilot.md#cluster-promotion-and-rollback)
uses a retained home volume and a private Tailscale route for WebSocket upgrades.
