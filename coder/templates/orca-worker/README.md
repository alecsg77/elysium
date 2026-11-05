---
displayname: Orca Worker
description: Project devcontainer with persistent home for remote Codex and OpenCode sessions
icon: /icon/openai.svg
tags: [kubernetes, devcontainer, ai]
---

# Orca Worker

Creates one project environment for an Orca SSH target. Coder clones the repository
and Envbuilder builds its devcontainer directly in the workspace Pod. The complete
`/home/coder` and `/workspaces` use separate workspace-scoped PVCs. Only the
Deployment follows Coder's start/stop count; both PVCs survive a workspace stop.

The project must provide Linux amd64 with glibc (for example Debian/Ubuntu), Bash, curl, tar, sha256sum, getent, cut,
mountpoint, and the account `coder` with UID/GID 1000 and home `/home/coder`.
Set `containerUser` and `remoteUser` to `coder` in `devcontainer.json`.
The setup fails if that account or the persistent mounts are missing.

Codex CLI is installed by `coder-labs/codex` without managing user configuration.
OpenCode is downloaded from a checksum-pinned upstream release. Neither installer
rewrites authentication. Authenticate Codex and OpenRouter in the workspace once;
their files, settings and histories then live in the persistent home.

Parameters select the HTTPS repository, devcontainer directory, CPU, memory, and
the size of each volume. The repository and disk size are immutable. GitHub
external authentication is optional and supplies private-clone credentials.

Envbuilder 1.3.0 requires a privileged Pod and is in upstream maintenance mode.
This pilot reuses the repository's existing approach while avoiding nested Docker
storage. Home is excluded from the in-place image build; install system tools in
the image, not into the mounted home during image construction. Nix can be added
to the project image later; non-interactive agent launches must activate its shell.

Deleting a Coder workspace can delete its Terraform-managed PVCs. Stop a workspace
to retain it; export or back up its data before deletion. This template does not
migrate or modify existing Mux workspaces.

See [Orca pilot](../../../docs/runbooks/orca-pilot.md) for connection and validation.
