---
displayname: Orca Worker
description: Project devcontainer with persistent home for remote Codex and OpenCode sessions
icon: /icon/openai.svg
tags: [kubernetes, devcontainer, ai]
---

# Orca Worker

Creates one project environment for an Orca SSH target. Coder clones the repository
and Envbuilder builds its devcontainer directly in the workspace Pod, reusing shared
registry layers when configured. The complete
`/home/coder` and `/workspaces` use separate workspace-scoped PVCs. Only the
Deployment follows Coder's start/stop count; both PVCs survive a workspace stop.

The project must provide Linux amd64 with glibc (for example Debian/Ubuntu), Bash, curl, tar, sha256sum, getent, cut, chown,
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

The checked-in cluster settings enable the existing internal registry's layer
cache. An unchanged Dockerfile and build context reuse cached installation layers;
Envbuilder still extracts the base image and starts the project lifecycle hooks.
Cache entries use Envbuilder content hashes and its default seven-day TTL; they
are separate from the SemVer releases under `images/`.

Cached builds use a fresh remote Git checkout as their build input. This excludes
uncommitted workspace files and keeps the provider's cache probe consistent with
the worker. Commit and push devcontainer changes to the repository/ref selected
when creating the workspace. Project edits and worktrees remain on their PVC;
Envbuilder does not reset that checkout. Set `cache_repo` empty to build local
uncommitted devcontainer changes instead.

Complete-image reuse is available through `use_cached_image`: a miss starts
Envbuilder and publishes the image; a hit starts its immutable digest. It is
currently disabled because the node runtime cannot resolve the registry's
ClusterIP DNS name. Enable it only after verifying native Kubernetes pulls,
including the runtime's HTTP/TLS settings. Pod-level access alone is insufficient.
The default layer-cache path does not need that node configuration.

Deleting a Coder workspace can delete its Terraform-managed PVCs. Stop a workspace
to retain it; export or back up its data before deletion. This template does not
migrate or modify existing Mux workspaces.

See [Orca pilot](../../../docs/runbooks/orca-pilot.md) for connection and validation.
