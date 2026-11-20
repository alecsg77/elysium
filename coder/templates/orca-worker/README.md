---
displayname: Orca Worker
description: Project devcontainer with a private Orca server and persistent Codex and OpenCode state
icon: /icon/openai.svg
tags: [kubernetes, devcontainer, ai]
---

# Orca Worker

Creates one project environment with its own Orca server. Coder clones the
repository and Envbuilder builds its devcontainer in the workspace pod. Orca
opens that checkout locally in the worker. The complete `/home/coder` and
`/workspaces` use separate workspace PVCs that survive a Coder stop/start.

The project must provide Linux amd64 with glibc (for example Debian/Ubuntu), Bash, curl, tar, sha256sum, getent, cut, chown,
mountpoint, and the account `coder` with UID/GID 1000 and home `/home/coder`.
Set `containerUser` and `remoteUser` to `coder` in `devcontainer.json`.
The setup fails if that account or the persistent mounts are missing.

Codex CLI 0.171.0 is installed by `coder-labs/codex` without managing user configuration.
OpenCode is downloaded from a checksum-pinned upstream release. Neither installer
rewrites authentication. Authenticate Codex and OpenRouter in the workspace once;
their files, settings and histories then live in the persistent home.

The Coder startup script installs the checksum-pinned Orca server and web bundle
from the same upstream release, starts Orca and imports `/workspaces/project`.
The installation, pairing state and logs live in `~/.local/share/orca`. The first
start downloads both upstream assets. Later starts reuse the installation.
Renovate proposes Codex CLI upgrades and updates the Orca release and both asset
checksums together in a separate PR.
The test-only profile under `~/.local/share/orca-coder-pilot` stays separate.
Git worktrees already on the workspace volumes remain available after re-pairing.

Open **Orca** from the workspace dashboard to pair the browser automatically.
The app is restricted to the owner by Coder and requires an HTTPS wildcard on
the Coder access domain. A loopback proxy issues the invite only on a
same-origin request from that app. Orca uses the fragment in the pairing link,
which stays out of proxy requests and logs.
If browser credentials need to be replaced, revisit the app root with
`?pair=1`. Use the **Open Orca** link on the setup page for manual pairing.

For desktop or mobile, use a private tunnel to port 6768. From the worker, run
`orca-ide pair --address ws://<private-tunnel-address>:<port>`, adding
`--mobile` for the phone. The Coder web app uses the browser's authenticated
session. Keep the private tunnel for native clients. The native listener is
reachable on pod interfaces and no Kubernetes Service is created for it.

Parameters select the HTTPS repository, devcontainer directory, CPU, memory, and
the size of each volume. The repository and disk size are immutable. GitHub
external authentication is optional and supplies private-clone credentials.

Envbuilder 1.3.0 requires a privileged Pod and is in upstream maintenance mode.
This pilot reuses the repository's existing approach while avoiding nested Docker
storage. Home is excluded from the in-place image build; install system tools in
the image, not into the mounted home during image construction. Nix can be added
to the project image later; non-interactive agent launches must activate its shell.

The cluster settings enable layer caching through the internal registry.
Envbuilder builds from the workspace checkout, so local devcontainer edits still
apply. Cached layers contain build outputs. Keep credentials out of the Docker
build context and avoid copying local secrets into the image. See the
[cache validation steps](../../../docs/runbooks/orca-pilot.md#validation-and-acceptance).

Deleting a Coder workspace can delete its Terraform-managed PVCs. Stop a workspace
to retain it; export or back up its data before deletion. This template does not
migrate or modify existing Mux workspaces.

See [Orca pilot](../../../docs/runbooks/orca-pilot.md) for connection and validation.
