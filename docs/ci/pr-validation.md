# PR Validation Workflows

This document describes the GitHub Actions workflows that validate pull requests before merge.
See `AGENTS.md` for the full command reference used by these workflows.

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
**Trigger:** `pull_request` on changes under `charts/**`.

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
helm plugin install https://github.com/helm-unittest/helm-unittest --version v1.1.2 --verify=false
helm unittest charts/cron-job
helm unittest charts/onechart
```
