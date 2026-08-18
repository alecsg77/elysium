---
name: github-actions-workflow-authoring
description: Create or change GitHub Actions workflows in this repository with reviewable YAML, testable CI helpers, and safe pull_request_target boundaries.
---

# GitHub Actions Workflow Authoring

## When To Use

Use this skill whenever creating or changing files under `.github/workflows/`,
workflow-local shell logic, Action dependencies, or helpers under `scripts/ci/`.

## Core rule: upstream tools first

Keep workflow YAML declarative and reviewable. Prefer a maintained upstream Action or
CLI plus declarative configuration before adding repository code. A short,
straight-line `run:` block may install a checksum-pinned tool, set environment
variables, or invoke standard validation commands directly; do not create a wrapper
that only reinterprets a standard tool's output.

Add a named helper under `scripts/ci/` only for a durable repository-specific
invariant that cannot be expressed directly and needs independent tests. Do not hide
large policy engines, scanner parsers, base/head ratchets, or retry state in inline
shell or helpers. If a helper is genuinely needed, keep proposed data inert and make
the boundary explicit.

## Helper Requirements

1. Put reusable CI shell helpers in `scripts/ci/` and begin with:

   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   ```

2. Provide `--help`/usage and validate required arguments. Use explicit output and
temporary-directory paths; never rely on ambiguous current-directory state.
3. Keep helpers inert with respect to PR data: parse manifests, render output, and
diffs as data; do not source, execute, or trust scripts/configuration from a proposed
checkout.
4. For `pull_request_target`, invoke helpers only from the trusted base checkout,
for example `bash base/scripts/ci/<helper>.sh`. A PR head checkout may be a data
input, never the source of executed CI code.
5. Prefer deterministic output formats (JSON or parsable text), pin downloaded tools
with checksum verification, and fail closed on malformed output, missing files, or
unexpected exit codes.
6. Add focused tests in `tests/ci/` for parsing, comparison, and policy decisions.
Test shell helpers with realistic temporary fixtures when their behavior is more than
simple argument forwarding. Always run `bash -n` and `shellcheck`.
7. Keep workflow commands small enough to review at a glance. If a reviewer must
trace state across more than a few straight-line commands, extract a helper.

## `pull_request_target` Checklist

- The workflow definition and every executed helper come from trusted `main`/base.
- Base and head SHAs are verified before comparison.
- Proposed files are never evaluated as executable shell, Python, Kustomize plugins,
  workflow configuration, or Action references.
- Reports/artifacts do not expose raw secret values, ciphertext, or unredacted code
  blocks from scanner output.
- Policy/configuration changes are separated from the manifests evaluated by that
  policy, and policy paths are protected as Tier 0 where appropriate.

## Review Checklist

Before committing a workflow change:

```bash
actionlint .github/workflows/<changed-workflow>.yml
yamllint .github/workflows/<changed-workflow>.yml
bash -n scripts/*.sh
```

When the change adds a real repository helper, run its focused tests and the smallest
meaningful end-to-end fixture or rendered input. Describe that helper boundary and
validation in the PR body.
