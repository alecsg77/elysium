# Additional Tool Installers

This directory holds standalone installer script **templates** for CLI tools that don't have an existing [Coder Registry module](https://registry.coder.com) covering them.

The scripts follow the same shape as [devcontainers/features `install.sh` scripts](https://github.com/devcontainers/features/blob/main/src/gh-cli/install.sh): a single pinned version with a `latest` escape hatch, no package manager assumptions, and an idempotency check up front. Unlike devcontainer features, the version is injected at plan time via Terraform's `templatefile()` rather than read from an env var at runtime.

## Convention

- One template per tool: `install-<tool>.sh.tftpl` (e.g. `install-gh-cli.sh.tftpl`). The `.tftpl` extension is required for `templatefile()`.
- **Version is pinned, not "always latest".** The template receives its version as a `version` variable from `templatefile()` in `main.tf`. It still accepts the literal value `latest` (for local testing) to resolve the newest release at runtime, but the steady-state value is always a pinned version tracked by Renovate.
- Escape literal `$` in the template as `$$` wherever it isn't meant to be interpolated by `templatefile()` (shell variables, parameter expansion, arithmetic). Only `${version}` (the passed-in variable) should use single `$`.
- Each script must be **idempotent** — detect a matching version already installed and skip re-installing; upgrade in place if a different version is installed.
- Each script must be **self-contained** — no `sudo`, no assumptions about a package manager being available (the envbox inner image may vary); prefer downloading a prebuilt binary release and installing it under `$HOME/.local/bin`.
- The only input is the `version` template variable — there's no other parameter to plumb through, so don't add env vars like `INSTALL_PREFIX` for values that are always the same in this template.
- Each script should exit non-zero only on unrecoverable errors, and print a clear status line on success.
- Start with `#!/usr/bin/env bash` and `set -euo pipefail`.

## Wiring into the template

Unlike modules, these scripts are **not auto-discovered**. `main.tf` declares an explicit, ordered list in the `local.tool_installers` block, one `templatefile()` call per tool. The pinned version is inlined directly in the `version = "..."` argument, with a trailing same-line comment marking it for Renovate — mirroring Flux's [image marker convention](https://fluxcd.io/flux/components/image/imageupdateautomations/#marking-images-for-update), which also places its marker comment on the same line as the value it updates:

```tf
templatefile("${path.module}/scripts/install-gh-cli.sh.tftpl", {
  version = "2.63.2" # renovate: datasource=github-releases depName=cli/cli extractVersion=^v(?<version>.+)$
}),
```

Adding a new tool means:

1. Add `scripts/install-<tool>.sh.tftpl` following the convention above.
2. Add a `templatefile(...)` entry to the `local.tool_installers` list in `main.tf`, with the pinned version inlined and a trailing `# renovate: datasource=... depName=...` marker on the same line (see the regex manager in `renovate.json` for supported fields: `datasource`, `depName`, `extractVersion`, `versioning`).

This is intentionally more manual than dynamic discovery — it keeps the list of installed tools and their pinned versions visible directly in `main.tf`, and lets Renovate track and bump each version independently via the marker, without a bespoke regex per tool in `renovate.json`.

## Testing a script locally

Render the template manually with a throwaway version to test:

```bash
sed 's/\${version}/latest/; s/\$\$/\$/g' coder/templates/mux/scripts/install-gh-cli.sh.tftpl | bash
```

Run `bun run shellcheck` from the repo root to lint all shell scripts, including these, before committing (note: it will not evaluate `.tftpl` interpolation syntax, so read the rendered output too for anything non-trivial).
