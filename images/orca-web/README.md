# Orca Web image

NGINX serves the upstream Orca 1.4.265 browser bundle. The build verifies the
Linux AppImage checksum and copies only the files in Orca's web asset manifest
plus its license. The container listens on port 8080 as UID/GID 101 and holds
no runtime configuration, account data, or pairing credentials.

The AI overlay publishes this app on the private Tailscale HTTPS ingress named
`orca-web`. To connect from that page, paste a runtime-scoped Orca pairing URL
for the server you want to use. Generate an invite interactively on that
server, using its browser-reachable `wss://` address. Keep the invite private.
The browser connects straight to the selected runtime.

Orca Web 1.4.265 saves one runtime per browser profile. Use **Clear saved
server** in the pairing screen to switch, or separate browser profiles for
multiple saved connections. The static container does not store them.

A server running inside Coder works with a browser-reachable WebSocket
endpoint. The Coder workspace app's own page and an independently hosted page
have different origins. The Coder login session may not be sent with a
cross-site WebSocket. Verify that connection before relying on the dashboard
URL, or give that runtime a private WSS route accessible to the browser.

When updating Orca, change the pinned AppImage version and checksum together,
check the web asset manifest, and increment the image's SemVer `VERSION`.
After merge, the image build publishes `1.0.0` to GHCR. Verify that the image is
pullable by the cluster and that Flux brings the Deployment and ingress up.
