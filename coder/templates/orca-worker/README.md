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

The project must provide an amd64 Debian or Ubuntu devcontainer with APT,
Bash, curl, sha256sum, getent, cut, chown, mountpoint, and the account
`coder` with UID/GID 1000 and home `/home/coder`. Set `containerUser`
and `remoteUser` to `coder` in `devcontainer.json`. The Coder template installs
the shared libraries for the packaged Orca CLI during Envbuilder setup.

Codex CLI 0.171.0 is installed by `coder-labs/codex` without managing user configuration.
OpenCode is downloaded from a checksum-pinned upstream release. Neither installer
rewrites authentication. Authenticate Codex and OpenRouter in the workspace once;
their files, settings and histories then live in the persistent home.

The Coder startup script unpacks the complete, checksum-pinned official Orca
Desktop `.deb` into the persistent home and runs `orca-ide serve` with
`orcad`. The same process serves the bundled Orca Web client and manages
`/workspaces/project`. It runs without a display server. Installation, pairing
state and logs live in `~/.local/share/orca`. Renovate updates the Orca version
and the matching Debian package checksum together.

For the first use in each browser profile, click **Genera link Orca Web**
on the Coder workspace dashboard. Open the link printed in the terminal
in the same browser profile that is signed in to Coder. On subsequent visits,
click **Orca Web**. Both apps are private to the workspace owner. The pairing
shortcut uses the deployment's wildcard HTTPS domain under the Coder
dashboard hostname.

Orca Desktop and Mobile can still connect through a private tunnel to port
6768. For native clients, use the reachable tunnel address instead of the
app hostname and add `--mobile` when pairing a phone. Keep pairing links
out of shared logs and messages.

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
