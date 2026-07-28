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
