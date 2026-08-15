---
name: github-actions-workflow-authoring
description: Create or change GitHub Actions workflows in this repository with reviewable YAML, testable CI helpers, and safe pull_request_target boundaries.
---

# GitHub Actions Workflow Authoring

## When To Use

Use this skill whenever creating or changing files under `.github/workflows/`,
workflow-local shell logic, Action dependencies, or helpers under `scripts/ci/`.

## Core Rule: Workflows Orchestrate; Helpers Implement

Keep workflow YAML declarative and reviewable. A `run:` block may install a tool,
set one or two environment variables, or invoke a helper. Move shell control flow
into a named, versioned helper under `scripts/ci/` when it has any of the following:

- functions, loops, branches, retries, traps, or non-trivial error handling;
- multiple commands whose output or exit status must be interpreted;
- input/argument parsing or temporary-file lifecycle management;
- security-sensitive diff, rendering, scanner, or credential-adjacent logic;
- logic that needs behavior tests beyond `bash -n` and ShellCheck.

Do **not** solve this by hiding a large inline script in a YAML folded scalar. The
workflow should show *which* trusted helper is called and *which inputs* it receives;
the helper should contain *how* the operation works.

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
python3 -m py_compile scripts/ci/*.py tests/ci/*.py
python3 -m unittest tests.ci.test_pr_gate_helpers tests.ci.test_critical_change_guard tests.ci.test_quality_ratchet tests.ci.test_quality_ratchet_shell
bash -n scripts/ci/*.sh
shellcheck scripts/ci/*.sh
actionlint .github/workflows/<changed-workflow>.yml
yamllint .github/workflows/<changed-workflow>.yml
```

Run the smallest meaningful end-to-end helper invocation with fixture or rendered
input as well. Describe the helper boundary and validation in the PR body.
