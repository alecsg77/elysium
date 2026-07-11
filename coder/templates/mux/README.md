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
| **Runtime** | `ghcr.io/coder/envbox:latest` (privileged, built-in Docker daemon) |
| **Inner image** | `codercom/enterprise-base:ubuntu` |
| **Mux** | Installed via `coder/mux` registry module (`mux@next` from npm) |
| **Storage** | Single PVC for `/home/coder`, Docker cache, and Mux state (`~/.mux`) |

## Modules

- [`coder/coder-login`](https://registry.coder.com/modules/coder/coder-login) — injects `CODER_SESSION_TOKEN` from the workspace owner automatically
- [`coder/mux`](https://registry.coder.com/modules/coder/mux) — installs and runs `mux server`, auto-generates `MUX_SERVER_AUTH_TOKEN`
- [`coder/devcontainers-cli`](https://registry.coder.com/modules/coder/devcontainers-cli) — installs `@devcontainers/cli`
- [`coder/git-config`](https://registry.coder.com/modules/coder/git-config) — configures git from Coder credentials
- [`coder/github-upload-public-key`](https://registry.coder.com/modules/coder/github-upload-public-key) — uploads SSH public key to GitHub (requires GitHub external auth)

## Prerequisites

- Kubernetes cluster with privileged pod support
- Coder deployment with GitHub external auth configured (optional, for SSH key upload)
