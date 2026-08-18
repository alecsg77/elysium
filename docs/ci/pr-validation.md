# PR Validation Workflows

This document describes the GitHub Actions workflows that validate pull requests before merge.
See `AGENTS.md` for the full command reference used by these workflows.

## Simple-gate shadow rollout

`PR Validate Simple / validate` is the non-required shadow gate for the
simplification rollout. It runs from `pull_request` with a read-only token, no
repository or environment secrets, and no cluster access. The workflow treats a
PR as reviewable homelab configuration rather than hostile code; the existing
trusted-base **PR Gate** remains the required merge boundary until the shadow
workflow passes the canary matrix and the ruleset is migrated.

The shadow workflow always runs yamllint, Gitleaks, and a source-level guard for
new or changed `kind: Secret` documents. It validates the Flux root and five
actual Flux apply surfaces with strict kubeconform only for GitOps changes, and
runs local-chart, Coder Terraform, or Actions/script checks only for their
respective paths. A short `actions/github-script` step queries the PR file list:
it replaces an external path-filter Action that is not permitted by the repository
Actions policy, without reintroducing a repository helper. The workflow has no
base/head quality ratchet, Checkov, custom report parser, critical-resource diff
engine, or fan-in state machine.

`.gitleaks.toml` permits only a complete Bitnami SealedSecret ciphertext-shaped
scalar line; normal plaintext in the same YAML file remains scanned. Because
Gitleaks evaluates line syntax rather than YAML structure, a deliberately added
plaintext value matching that ciphertext shape is an accepted, narrow residual
risk. The tracked `apps/base/coder/secret.yaml` is historical plaintext-Secret
debt and is not allowed to change. It requires a separate credential rotation
and SealedSecret/native-reference migration before the simplified source-level
guard can be made whole-tree strict.

Do not make `PR Validate Simple / validate` required or remove `PR Gate /
required` until a fresh canary PR validates documentation-only, GitOps,
SealedSecret rotation, chart, Coder, and Actions/script changes.

## Current merge boundary

The repository's current required merge boundary is **`PR Gate / required`**.
Its **`required`** job detects the paths changed by a PR, runs baseline and applicable
domain validators, and fails closed when a selected validator does not succeed. The
ruleset requires this one job context rather than path-filtered workflow contexts.

The legacy path-filtered workflows remain temporarily for diagnostic continuity,
but they are not merge requirements. Do not add their individual job names as
additional required checks. Retire them only in a follow-up PR after confirming the
PR Gate continues to cover each legacy validation domain. See [Merge and auto-merge
policy](merge-and-automerge-policy.md) for the agent flow and [Destructive GitOps
changes](../runbooks/destructive-gitops-change.md) for the R2 procedure.

## `PR Gate` fan-in behavior

The repository ruleset requires the `required` job from this workflow after the
workflow reached the default branch and passed the documentation-only rollout PR
#95. That rollout verified baseline and critical success, intentional skips by the
conditional validators, and the final fail-closed fan-in. The legacy path-filtered
workflows remain diagnostic only; they are not merge requirements.

`pr-gate.yml` is loaded from the trusted default branch with
`pull_request_target`. It checks out the proposed head SHA only as data, uses
read-only permissions, disables persistent checkout credentials, and does not use
production secrets or mutate the cluster. Its jobs are:

- **baseline** — trusted YAML quality ratchet, YAML parsing, bare-Secret rejection,
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

### Trusted PR Gate helpers

The security-sensitive logic that would otherwise make `pr-gate.yml` difficult to
review lives under `scripts/ci/` with focused tests under `tests/ci/`. The
`pull_request_target` PR Gate always invokes helpers from its trusted base checkout
(`base/scripts/ci/...`); it never executes a helper from the proposed checkout.
The non-privileged `PR Validate CI Helpers` workflow runs the proposed helper tests
on PRs that change those files.

Run the equivalent checks locally before opening such a PR:

```bash
python3 -m py_compile scripts/ci/*.py tests/ci/*.py
python3 -m unittest tests.ci.test_pr_gate_helpers tests.ci.test_critical_change_guard tests.ci.test_quality_ratchet tests.ci.test_quality_ratchet_shell tests.ci.test_split_rendered_manifests
bash -n scripts/ci/*.sh
shellcheck scripts/ci/*.sh
```

The helpers deliberately treat PR manifests, YAML, Terraform, rendered output, and
Git diffs as data. In particular, the Secret and Gitleaks helpers operate on explicit
verified SHA-to-SHA Git data; they do not load a PR-controlled `.gitleaks*` file or
execute PR scripts.

## Transitional quality ratchet

The GitOps validation backlog is being remediated while ordinary releases continue.
During this transition, PR Gate compares trusted scans of the PR base revision and
proposed head rather than treating historical debt as an implicit permanent allowlist.

For **yamllint**, **kubeconform**, and Kubernetes **Checkov**:

- a finding already present and unchanged on the trusted PR base is reported as
  inherited debt and does not block an unrelated release;
- a finding removed by the PR is reported as debt reduction;
- any new finding, additional duplicate occurrence, missing-schema record, malformed
  report, scan failure, or render failure blocks the applicable PR Gate job;
- a finding may not be traded for a different finding in the same PR: comparison is
  by normalized identity, not by a total count.

The job summary and `quality-ratchet-*.json` artifacts report one of `PASS CLEAN`,
`PASS WITH EXISTING DEBT`, `PASS WITH DEBT REDUCTION`, `FAIL: NEW DEBT`, or
`FAIL: POLICY CHANGES FINDING SET` for each validator. The report stores normalized
identities and hashes, not raw YAML lines or secret values.

Consequently, a green `PR Gate / required` means **no new quality debt relative to
its trusted base** during the transition; it does not claim that all historic findings
are gone. When every baseline reaches zero (apart from documented resource-scoped
exceptions), the ratchet will be simplified to strict validation and a green gate will
again mean zero unsuppressed findings.

### Trust and change-separation boundary

The `pull_request_target` gate renders and scans both trees with helpers, tool
versions, YAML configuration, and schema locations from the trusted base checkout.
The proposed checkout is input data only. Quality-policy paths—PR Gate, ratchet and
other CI helpers, `.yamllint.yaml`, trusted `.github/checkov.yaml`, critical-resource
policy, and local schemas—are Tier 0. Checkov scans explicitly use the base checkout
configuration, so a PR-root `.checkov.yaml` cannot change either scan. A PR that
changes quality policy and manifests/functions evaluated by that policy is rejected;
split it into a policy PR and a separately evaluated content PR.

A `.yamllint.yaml` policy-only PR is additionally evaluated against the current
trusted manifest tree with both the old and proposed configuration. It fails if the
new policy suppresses inherited findings or exposes additional current findings, so a
policy merge cannot silently rewrite the ratchet baseline.

Kubeconform uses a checksum-pinned binary and a commit-pinned Datree CRD catalog
reference for both sides of a comparison. Updating a schema source, tool version, or
local schema is itself a quality-policy-only change and must publish its effect on the
current trusted base before it can govern manifest changes.


Kubeconform accepts ordered schema locations. The trusted scan consults Kubernetes'
default schemas first, then repository-local schemas when present, and finally the
commit-pinned Datree catalog. A PR that changes the PR Gate catalog pin or local
schema files is scanned a second time against the same trusted rendered base: the
base policy uses trusted locations while the candidate policy is parsed from the
proposed workflow and schema files only as inert data. The comparison publishes any
resulting finding reduction or regression before that policy can govern later
manifest PRs; proposed workflow or helper code is never executed by this step.


The local native `CustomResourceDefinition` schema is derived from the Kubernetes
`v1.36.3` OpenAPI v3 artifact and has provenance plus an artifact checksum in
`.github/schemas/`. The PR Gate verifies that trusted bundle before the ordinary
comparison. A candidate local-schema PR also has to reject a trusted, synthetic CRD
with an unknown top-level field; this prevents a schema refresh from making the
native CRD envelope silently permissive. The schema resolves only
`apiextensions.k8s.io/v1/CustomResourceDefinition`; the Datree catalog continues to
validate other custom-resource kinds.

PRs may continue to merge while this work proceeds. A rebase or new commit simply
reruns comparison against the newer trusted base, so a finding fixed by another PR
cannot be reintroduced as inherited debt.

## Level 1 — repository-wide checks (always run on every PR)

### YAML lint (`pr-lint-yaml.yml`)
- **What it checks:** Runs `yamllint -c .yamllint.yaml clusters/ infrastructure/ apps/ monitoring/` against every pull request, regardless of which paths changed. It remains a diagnostic workflow; the required PR Gate baseline runs the trusted base/head quality ratchet and blocks new lint errors or warnings while allowing unchanged historical findings temporarily.
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
would leave the check permanently "Pending" and block merge. The always-present PR
Gate supplies the merge requirement instead.

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
> neither filtered path leaves the check permanently "Pending", which blocks merge. The
> always-present PR Gate supplies the merge requirement instead.

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
it must **not** be an individual required status check: the always-running PR Gate
provides the merge requirement instead.

The workflow validates the core GitOps directories with four jobs:

1. **`kustomize-build`** — runs `kustomize build` for each `apps/kyrion/<namespace>` overlay and
   the infrastructure and monitoring targets. `monitoring/controllers` is rendered through a
   temporary recursive Kustomization because it has no aggregating `kustomization.yaml`.
2. **`flux-build`** — runs `flux build kustomization` for `apps`, `infra-controllers`,
   `infra-configs`, `monitoring-controllers`, and `monitoring-configs`, using each resource's own
   `spec.path` and Kustomization manifest.
3. **`validate-manifests`** — checks the rendered artifacts with kubeconform and Checkov.
   This legacy workflow remains diagnostic-only. The required PR Gate now scans both trusted base and
   proposed render output, blocks newly introduced kubeconform/Checkov debt, and reports unchanged
   historical findings as transitional debt while the real backlog tracked in #66 is remediated.
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
