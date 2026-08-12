# PR Validation Workflows

This document describes the GitHub Actions workflows that validate pull requests before merge.
See `AGENTS.md` for the full command reference used by these workflows.

## Current merge boundary

The repository is moving to one always-present monorepo workflow:
**`PR Gate / required`**. It detects the paths changed by a PR, runs baseline and
applicable domain validators, and fails closed when a selected validator does not
succeed. The ruleset requires this one context rather than path-filtered workflow
contexts.

The legacy path-filtered workflows remain temporarily for diagnostic continuity
while the ruleset is migrated, but they are not merge requirements. Do not add
their individual job names as additional required checks; once the GitHub ruleset
requires `PR Gate / required`, they can be retired in a follow-up PR. See [Merge
and auto-merge policy](merge-and-automerge-policy.md) for the agent flow and
[Destructive GitOps changes](../runbooks/destructive-gitops-change.md) for the R2
procedure.

## `PR Gate` fan-in behavior

The target ruleset configuration is intentionally enabled only after this workflow
has reached the default branch and passed a test PR. Until that server-side step is
complete, the workflow is diagnostic and repository policy still requires agents to
use PRs and native auto-merge voluntarily.

`pr-gate.yml` is loaded from the trusted default branch with
`pull_request_target`. It checks out the proposed head SHA only as data, uses
read-only permissions, disables persistent checkout credentials, and does not use
production secrets or mutate the cluster. Its jobs are:

- **baseline** — trusted YAML configuration, YAML parsing, bare-Secret rejection,
  and gitleaks;
- **critical** — the trusted-base rendered-diff guard, including root-composition,
  dependency, remote-base, R1/R2, and intent checks;
- **GitOps, Helm, Coder, Actions/scripts, functions** — conditional validators;
- **required** — the only status context configured in the ruleset. It fails if a
  selected validator fails, is cancelled, or unexpectedly skips.

A change to a Tier 0 enforcement path—workflow, guard, guard policy,
`.github/actionlint.yaml`, or `CODEOWNERS`—selects every domain validator. This
prevents an enforcement-boundary change from being validated by only its own
narrow job. The Coder validator consequently validates every current template when
Tier 0 changes select that domain.

## Level 1 — repository-wide checks (always run on every PR)

### YAML lint (`pr-lint-yaml.yml`)
- **What it checks:** Runs `yamllint -c .yamllint.yaml clusters/ infrastructure/ apps/ monitoring/` against every pull request, regardless of which paths changed. Unlike the non-blocking yamllint step in `copilot-setup-steps.yml`, this workflow fails the job (and blocks the PR) on any lint error.
- **Local equivalent:** `yamllint -c .yamllint.yaml clusters/ infrastructure/ apps/ monitoring/` (or `yamllint .` per `AGENTS.md`'s "Essential Commands" for a repo-wide pass).

### Secret scan (`pr-secret-scan.yml`)
- **What it checks:** Runs [`gitleaks/gitleaks-action`](https://github.com/gitleaks/gitleaks-action) against the PR diff to catch accidentally committed plaintext secrets, credentials, or tokens — independent of which paths changed.
- **Local equivalent:** Install [gitleaks](https://github.com/gitleaks/gitleaks) and run `gitleaks detect --source . -v` (or `gitleaks protect --staged -v` before committing) to scan for secrets before opening a PR.

## Level 2 — domain-specific checks (path-filtered)

### `pr-validate-charts.yml` — Helm chart lint and unit tests

**Workflow:** `.github/workflows/pr-validate-charts.yml`
**Trigger:** `pull_request` on changes under `charts/**` (the workflow file's own path is
also included in the filter so changes to its logic are validated too). Note that this
`paths:` filter is trigger-level only — it does not make this workflow safe to mark as a
required status check in branch protection, since a PR that doesn't touch these paths
would leave the check permanently "Pending" and block merge; see #67 for the fan-in
"gate" job refactor needed before this workflow can be required.

Validates the vendored Helm charts (`charts/cron-job`, `charts/onechart`):

- **`ct lint`** ([`helm/chart-testing-action`](https://github.com/helm/chart-testing-action)): auto-detects which
  chart(s) changed relative to `main` and runs `helm lint` plus chart schema/`values.schema.json` validation against
  each. Configured via the repo-root `ct.yaml` (`check-version-increment: false`, since these charts track the
  vendored Gimlet `onechart` upstream version rather than an independent local semver; `validate-maintainers: false`,
  since the vendored `Chart.yaml` files don't declare a `maintainers` field).
- **`helm unittest`** ([`helm-unittest`](https://github.com/helm-unittest/helm-unittest) plugin): runs the
  `suite:`/`tests:`/`asserts:` test files under `charts/*/tests/*_test.yaml` against both charts.

**Local equivalent:**

```bash
# Lint only the chart(s) changed vs. main (matches the ct lint step)
ct lint --config ct.yaml --target-branch main

# Or lint a single chart directly with Helm (no ct required)
helm lint charts/onechart

# Run the existing helm-unittest suite for a chart (requires the helm-unittest plugin)
# --verify=false: the plugin source doesn't support provenance verification, which newer
# Helm CLIs require by default
helm plugin install https://github.com/helm-unittest/helm-unittest --version v1.1.2 --verify=false
helm unittest charts/cron-job
helm unittest charts/onechart
```

### `pr-validate-coder-templates.yml`

Triggers on `pull_request` when files under `coder/templates/**` or the workflow file itself
(`.github/workflows/pr-validate-coder-templates.yml`) change. Each `coder/templates/<name>/`
directory is an independent Terraform root module (no remote backend, no shared provider config).

> **Note:** the `paths:` filter above only controls when the workflow *triggers* — it does not make
> this workflow safe to mark as a required status check in branch protection. A PR that touches
> neither filtered path leaves the check permanently "Pending", which blocks merge. See
> [#67](https://github.com/alecsg77/elysium/issues/67) for the proper fix (a fan-in "gate" job
> pattern).

The workflow first computes which template directories were touched by the PR (diffing the PR's
base and head refs, same approach as the `init` job in `publish-coder-templates.yaml` but adapted to
`pull_request`), then runs the checks below in a matrix, once per changed template. Unlike
`publish-coder-templates.yaml`, this workflow never runs `coder templates push` and never uses the
`CODER_SESSION_TOKEN` secret — it is validation-only and safe to run on PRs from forks.

For each changed template:
- `terraform fmt -check -recursive` — fails the job if the template isn't formatted.
- `terraform init -backend=false` — initializes providers without requiring backend credentials.
- `terraform validate` — checks the configuration is syntactically valid and internally consistent.
- [Checkov](https://www.checkov.io/) (`framework: terraform`) — scans the template directory for
  security/best-practice misconfigurations. **Non-blocking for now** (`soft_fail: true`): Checkov
  reports real, pre-existing Kubernetes pod security-posture findings (missing probes, no
  read-only root filesystem, `NET_RAW` not dropped, images not pinned by digest, etc.) on all 6
  templates. These are genuine gaps in currently-running Coder workspace templates, not false
  positives, but fixing them requires careful per-template testing to avoid breaking active dev
  workspaces, which is out of scope for this validation-only workflow. Tracked in
  [#65](https://github.com/alecsg77/elysium/issues/65); once the backlog is cleared, `soft_fail`
  should be removed so Checkov blocks regressions again.
- A **non-blocking** check of the `README.md` frontmatter (`displayname`/`description`/`icon`, read
  via the same `mheap/markdown-meta-action` used in `publish-coder-templates.yaml`) that emits a
  `::warning::` annotation if a field looks missing. It never fails the job — the publish workflow
  already consumes these fields silently, so this is just an early heads-up.

`tflint` is intentionally not included: `terraform validate` and Checkov already cover
configuration correctness and security posture for these templates, and adding `tflint` would
require introducing and maintaining a separate ruleset with no rules currently defined for this
repo. It can be added later as an additional step if a concrete need arises.

Local equivalent (run from a changed `coder/templates/<name>/` directory):
```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
checkov -d . --framework terraform --soft-fail
```

### `pr-validate-flux.yml` — Flux and rendered-manifest validation

**Workflow:** `.github/workflows/pr-validate-flux.yml`
**Trigger:** `pull_request` on changes under `clusters/**`, `infrastructure/**`, `apps/**`, or
`monitoring/**`, as well as changes to this workflow file. Like the other path-filtered workflows,
it must **not** be a required status check until #67 introduces an always-running fan-in gate.

The workflow validates the core GitOps directories with four jobs:

1. **`kustomize-build`** — runs `kustomize build` for each `apps/kyrion/<namespace>` overlay and
   the infrastructure and monitoring targets. `monitoring/controllers` is rendered through a
   temporary recursive Kustomization because it has no aggregating `kustomization.yaml`.
2. **`flux-build`** — runs `flux build kustomization` for `apps`, `infra-controllers`,
   `infra-configs`, `monitoring-controllers`, and `monitoring-configs`, using each resource's own
   `spec.path` and Kustomization manifest.
3. **`validate-manifests`** — checks the rendered artifacts with kubeconform and Checkov.
   Kubeconform remains non-blocking because strict CRD schemas can reject valid SealedSecrets;
   Checkov remains non-blocking while the real pre-existing findings tracked in #66 are remediated.
4. **`no-plaintext-secrets`** — rejects a literal `kind: Secret` added to changed YAML under
   `apps/**` or `clusters/**`; `SealedSecret` resources remain permitted.

**Local equivalents:**

```bash
kustomize build apps/kyrion/<namespace>/
flux build kustomization apps --path ./apps/kyrion --kustomization-file clusters/kyrion/apps.yaml --dry-run
kubeconform -strict -ignore-missing-schemas <rendered-file-or-dir>
checkov -d <rendered-dir> --framework kubernetes --soft-fail
```

**Known limitation:** `flux build kustomization` emits `HelmRelease` custom resources but does not
render their referenced Helm charts. Issue #60 tracks evaluating `flate`, `konflate`, or another
maintained renderer for this gap.
