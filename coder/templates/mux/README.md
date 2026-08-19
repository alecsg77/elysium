---
displayname: Mux
description: AI coding agent multiplexer workspace with Docker support via envbox
icon: /icon/mux.svg
tags: [kubernetes, envbox, mux, docker, ai]
---

# Mux

Provisions a Kubernetes workspace running [Mux](https://github.com/coder/mux) — Coder's AI coding agent multiplexer — inside an [envbox](https://github.com/coder/envbox) container that provides a full Docker environment without a separate sidecar.

## Architecture

| Component | Details |
|---|---|
| **Runtime** | `ghcr.io/coder/envbox:0.6.7` (privileged, built-in Docker daemon) |
| **Inner image** | `codercom/enterprise-node:ubuntu-20260713` |
| **Mux** | Installed via `coder/mux` registry module (pinned from npm and Renovate-managed) |
| **Storage** | Single PVC for `/home/coder`, Docker cache, and Mux state (`~/.mux`) |

## Docker cache stability

The inner Docker daemon uses Docker's classic image store (`containerd-snapshotter=false`) while retaining the existing home-PVC cache layout. Envbox's outer Docker daemon continues to use its separate home-PVC path; replacing that outer configuration would remove Envbox's required `sysbox-runc` runtime.

This configuration was validated in a dedicated canary on August 6, 2026 across serialized builds, a normal workspace restart with cache reuse, simultaneous builds from separate worktrees, a deliberately interrupted no-cache build, and a subsequent rebuild. The original containerd snapshotter path had reproduced missing content-digest and snapshot errors after a normal workspace restart.

The workspace continues using the existing `cache/docker-v2` home-PVC subpath, preserving the separate outer Envbox Docker path and avoiding a storage migration. The older cache subpath remains untouched for forensic retention and can be removed only through a separately approved cleanup.

## Modules

- [`coder/coder-login`](https://registry.coder.com/modules/coder/coder-login) — injects `CODER_SESSION_TOKEN` from the workspace owner automatically
- [`coder/mux`](https://registry.coder.com/modules/coder/mux) — installs and runs `mux server`, auto-generates `MUX_SERVER_AUTH_TOKEN`
- [`coder/devcontainers-cli`](https://registry.coder.com/modules/coder/devcontainers-cli) — installs `@devcontainers/cli`
- [`coder/git-config`](https://registry.coder.com/modules/coder/git-config) — configures git from Coder credentials
- [`coder/github-upload-public-key`](https://registry.coder.com/modules/coder/github-upload-public-key) — uploads SSH public key to GitHub (requires GitHub external auth)

## Additional tool installers

For CLI tools without an existing Coder Registry module (e.g. GitHub CLI `gh`), standalone installer script templates live under [`scripts/`](./scripts). Each `scripts/install-<tool>.sh.tftpl` is rendered via `templatefile()` with a pinned version and run as part of a single `coder_script` on startup. Versions are pinned as `main.tf` locals decorated with `renovate:` comments so Renovate can bump them automatically — see [`scripts/README.md`](./scripts/README.md) for the full convention.

## Docker and BuildKit diagnostics

The startup script installs two non-destructive tools in `~/.local/bin`:

- `collect-mux-docker-state [label]` captures Docker/BuildKit versions, cache metadata, mount and capacity data, and relevant daemon logs under `~/.mux/docker-diagnostics/`.
- `devcontainer-observed <devcontainer arguments>` runs the standard Dev Containers CLI, retains the complete command/output, and automatically invokes the collector if the command fails.

Use `devcontainer-observed up --workspace-folder .` when investigating a failure. Neither tool prunes cache, deletes containers, or changes Docker state.

## Local Mux API access

The template binds the Mux server to IPv4 loopback and exports its loopback URL for workspace commands. This keeps the API private to the workspace network namespace while allowing `mux api` commands to use the same address family as the server.

## Workspace ServiceAccount

The template assigns an existing ServiceAccount named for the workspace owner to every workspace Pod. The template does not create the ServiceAccount, RBAC bindings, or credentials; provisioning fails if the expected ServiceAccount is unavailable.

The template forwards the Pod's projected ServiceAccount directory to the Envbox inner container as a read-only runtime mount, together with the Kubernetes service-discovery environment variables required for in-cluster clients. The credential remains ephemeral and outside the persistent home and cache volumes. The repository's shared Dev Container configuration passes the same read-only mount and discovery variables into child devcontainers, so devcontainers launched from Mux can use the workspace identity.

## Prerequisites

- Kubernetes cluster with privileged pod support
- Coder deployment with GitHub external auth configured (optional, for SSH key upload)
