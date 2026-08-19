You are an experienced, pragmatic software engineering AI agent. Do not over-engineer a solution when a simple one is possible. Keep edits minimal. If you want an exception to ANY rule, you MUST stop and get permission first.

# Elysium Agent Guide

Vendor-neutral operating guide for AI coding agents working in this repository.

## Project Overview
- **Elysium** is a GitOps-managed Kubernetes homelab (cluster name `kyrion`, a k3s cluster) reconciled entirely by [Flux](https://fluxcd.io/).
- Its primary purpose is learning and experimentation. Production patterns may be implemented to study them, but production-grade availability, durability, and hardening are not default requirements. Prefer the simplest upstream-supported solution whose maintenance cost is proportionate to the homelab risk; distinguish component requirements from optional hardening and record accepted tradeoffs explicitly.
- There is no application source code to compile here — the repo is a monorepo of Kubernetes manifests, Helm values, Kustomize overlays, and small Helm charts. "Building" means rendering manifests locally to catch errors before they reach the cluster.
- Technology stack: **Flux** (Kustomization/HelmRelease CRDs), **Kustomize** (base/overlay composition), **Helm** (third-party charts + two local charts under `charts/`), **Bitnami Sealed Secrets** (encrypted secrets in Git), **Terraform** (Coder workspace templates under `coder/templates/`), YAML/yamllint for formatting.
- Goals: single source of truth in Git, safe-by-default (no plaintext secrets, no direct `kubectl apply`), and a clean base/overlay separation so apps are reusable across environments.

## Reference
- `AGENTS.md` (this file) — portable baseline for all agents. `.github/copilot-instructions.md` is the Copilot-specific overlay; `CLAUDE.md` bootstraps Claude Code into this file.
- `docs/README.md` — documentation index; `docs/standards/repository-structure.md` is the **authoritative** guide to where any given file belongs (read it before adding new manifests).
- Top-level directories:
  | Path | Purpose |
  |------|---------|
  | `clusters/kyrion/` | Flux entry point: `Kustomization` objects defining what gets applied and in what order. |
  | `infrastructure/` | Controllers/operators (`controllers/`) and their cluster-wide config (`configs/`). |
  | `apps/base/<app>/` | Environment-agnostic app catalog (namespace-agnostic, no cluster-specific values). |
  | `apps/kyrion/<namespace>/` | Per-namespace overlay: selects apps from the catalog, sets namespace + cluster-specific patches. |
  | `monitoring/` | Observability stack (controllers + configs): Grafana, kube-prometheus-stack, Loki, etc. |
  | `charts/` | Local Helm charts (`cron-job`, `onechart`) consumed by apps. |
  | `coder/templates/` | Terraform templates for Coder-provisioned dev/agent workspaces. |
  | `functions/` | Fission serverless function specs. |
  | `etc/` | Local operator artifacts (kubeconfig, certs) — never commit private keys. |
  | `scripts/` | Bootstrap/automation scripts (e.g. `bootstrap_flux.sh`, `collect-monitoring-baseline.sh`). |
  | `docs/` | Human documentation: architecture, standards, runbooks, security, troubleshooting. |
- Skills referenced below live under `.agents/skills/<name>/SKILL.md` (moved there from `.github/skills/` in commit `cc947d7`; all `/docs` and `.github/instructions/*.md` references were updated to match). mux discovers `.agents/skills/` natively (see "Mux-Specific Notes" below).

## Scope
- Apply these rules when modifying code, manifests, documentation, or automation in this repository.
- This file is the portable baseline for non-Copilot agents.
- `.github/copilot-instructions.md` is the Copilot-specific overlay and remains the primary entry point for GitHub Copilot.

## Source Of Truth
- Authoritative human and operational documentation lives under `/docs`.
- Machine-oriented Copilot customizations live under `/.github`.
- If your host does not understand Copilot frontmatter or custom agent metadata, ignore the YAML metadata and follow the markdown body and linked `/docs` content.

## Core Repository Rules
- This is a GitOps repository. Cluster changes must flow through Git, not direct `kubectl apply` mutations.
- Never commit plaintext secrets. Use Sealed Secrets.
- Treat infrastructure identifiers as sensitive because this repository is public: do not commit real host/device names, private domains, internal addresses or endpoints, or topology details. Use placeholders, Git-ignored local configuration, and Secrets/Sealed Secrets; include a real identifier only when strictly necessary and explicitly approved, and review diffs for accidental disclosure before release.
- Respect the base/overlay split:
  - Base: `apps/base/<app>/`
  - Environment overlay: `apps/kyrion/`
- Infrastructure is a shared catalog: `infrastructure/controllers` installs platform APIs/controllers and `infrastructure/configs` instantiates/configures them. Cluster wrappers under `clusters/<cluster>/infrastructure/` may parameterize the complete catalog but must not select components, alter namespaces, or add/remove functional infrastructure. Follow `docs/standards/infrastructure-organization.md`.
- Deliver secret values via a consumer-native Secret reference or HelmRelease `valuesFrom` before considering Flux post-build substitution; reserve substitution for sensitive raw identifier composition that has no native reference.
- Respect Flux dependency ordering: controllers/CRDs before dependent resources.
- Keep documentation authoritative in `/docs`, not duplicated across agent files.

## Pull Request and Auto-Merge Safety
- Never commit or push directly to `main`, including when authenticated as a repository administrator. Agents may commit to a feature branch and open/update a PR after running the applicable validation.
- Opening a PR is **not** by itself permission to merge. Merge authorization may come from an explicitly approved implementation plan when the PR is wholly within that plan, or from an explicit approval of the PR itself. Record the authorization source and scope in the PR template.
- Approval of an implementation plan automatically authorizes native squash auto-merge for a PR that wholly implements that plan; no redundant per-PR or per-SHA approval is required. A PR with changes outside the approved plan must remain available for the user's final PR-level review and approval.
- Explicit PR approval remains valid for any descendant head SHA produced solely by rebasing onto, or merging from, `main`. Do not disable auto-merge or request renewed approval for that mechanical branch synchronization.
- Any other substantive change pushed after approval is not covered automatically. Leave or return auto-merge to disabled, present the updated PR for the user's final review, and obtain PR-level approval before enabling native squash auto-merge with `gh pr merge --auto --squash`. Never manually merge.
- Never use `gh pr merge --admin`, a direct merge API bypass, or a force push as a routine workaround. The only break-glass path is documented in `docs/runbooks/github-break-glass.md`.
- `PR Validate Simple / validate` and `Flux Bootstrap Guard / guard` are required. The simple check always runs YAML lint, Gitleaks, and the plaintext-Secret guard; it adds GitOps rendering, local-chart, Coder Terraform, or Actions/script validation only for relevant paths. The bootstrap guard runs from trusted `main` and freezes the Flux source/root-composition files. Together they do not certify production-grade hardening or remote Helm chart rendering.
- Treat changes to Flux bootstrap/ownership, Tailscale access resources, secrets, storage, and CI guardrail files as critical. For data or recovery-access resources protected by a Flux/Kubernetes/Helm retention annotation, follow `docs/runbooks/destructive-gitops-change.md`; persistent-data changes additionally require the backup/restore contract in `docs/runbooks/backup-and-restore.md`.

## Essential Commands
This repo has no application build/test suite — "validation" means rendering manifests locally and linting YAML.
- **Render/build a single app**: `kustomize build apps/base/<app>/`
- **Render a full namespace overlay**: `kustomize build apps/kyrion/<namespace>/`
- **Render exactly what Flux will apply**: `flux build kustomization apps --path clusters/kyrion`
- **Render a HelmRelease's chart** (when adding/upgrading one): `helm template <name> <chart> -f values.yaml`
- **Lint YAML**: `yamllint .` (config in `.yamllint.yaml`; `.md` files and `clusters/*/flux-system/` are excluded)
- **Validate `renovate.json`**: `renovate-config-validator` (Renovate CLI is preinstalled in the devcontainer via `ghcr.io/devcontainers-extra/features/renovate-cli:2`; outside the devcontainer, run `npx --yes --package renovate -- renovate-config-validator` instead)
- **Dry-run Renovate locally** (see what updates it would open, without pushing anything): `LOG_LEVEL=debug RENOVATE_PLATFORM=local renovate` from the repo root
- **Lint a local Helm chart** (`charts/cron-job`, `charts/onechart`): `helm lint <chart>`
- **Run a local chart's `helm-unittest` suite**: `helm unittest <chart>` (e.g. `helm unittest charts/onechart`); requires the `helm-unittest` plugin (`helm plugin install https://github.com/helm-unittest/helm-unittest`)
- **Bootstrap Flux on a new cluster** (rarely needed, destructive on a fresh cluster only): `scripts/bootstrap_flux.sh`
- **Collect a monitoring baseline** (for troubleshooting/regressions): `scripts/collect-monitoring-baseline.sh`
- There is no `clean`, `format`, or dev server target — YAML/Helm files are edited directly and validated via the render commands above.
- For troubleshooting, prefer the smallest diagnostic command set that can identify the first failing control point (see `.agents/skills/troubleshoot-flux/SKILL.md`).

## Cross-Agent Compatibility Rules
- Keep Copilot-specific files valid for Copilot first.
- For portability, prefer reusable guidance in `/docs`, `AGENTS.md`, `CLAUDE.md`, and plain markdown `SKILL.md` bodies.
- Treat `.agents/skills/<name>/SKILL.md` as reusable workflow references even if your host does not natively support skills.
- Treat `.github/agents/*.agents.md` as role/workflow references if your host does not support custom agent frontmatter.

## Primary Workflows
- Deploy application: `.agents/skills/deploy-application/SKILL.md`
- Manage sealed secrets: `.agents/skills/manage-sealed-secrets/SKILL.md`
- Generate docs: `.agents/skills/generate-gitops-docs/SKILL.md`
- Review GitOps config: `.agents/skills/review-gitops-config/SKILL.md`
- Plan GitOps work: `.agents/skills/gitops-implementation-planning/SKILL.md`
- Search historical incidents: `.agents/skills/knowledge-base-search/SKILL.md`
- Troubleshoot Flux and Kubernetes issues: `.agents/skills/troubleshoot-flux/SKILL.md`
- Author GitHub Actions workflows: `.agents/skills/github-actions-workflow-authoring/SKILL.md`
- Create/update Coder workspace templates: `.agents/skills/coder-templates/SKILL.md`

## PR Validation Workflow
- `.github/workflows/pr-validate-simple.yml` publishes the general required context: `PR Validate Simple / validate`.
- `.github/workflows/flux-bootstrap-guard.yml` publishes `Flux Bootstrap Guard / guard`, a trusted-base required context that freezes the Flux root/source files and its own workflow.
- The simple workflow always runs YAML lint, Gitleaks, and the plaintext-Secret guard. It runs Flux/Kustomize rendering with strict kubeconform for GitOps paths, Helm lint/unit tests for local-chart paths, Terraform validation for Coder-template paths, and actionlint plus shell syntax checks for workflow/script paths.
- Keep both workflows small and direct: use maintained upstream tools and declarative configuration before adding a repository helper. A bootstrap recovery uses the documented break-glass path rather than weakening the ordinary PR gate.
- See `docs/ci/pr-validation.md` for the validator matrix and `docs/ci/merge-and-automerge-policy.md` for the merge flow.

## GitHub Actions Workflow Authoring
- Prefer maintained upstream Actions/CLIs and declarative configuration. Small straight-line commands that invoke standard tools may remain in a workflow; add a `scripts/ci/` helper only for a durable repository-specific invariant that needs its own tests.
- For any `.github/workflows/**` or `scripts/ci/**` change, load `.agents/skills/github-actions-workflow-authoring/SKILL.md`. In `pull_request_target`, invoke only helpers from the trusted base checkout (for example `base/scripts/ci/...`); PR content is data and must never become executable CI code.

## Copilot-Specific Workflows
- Copilot is the primary hosted workflow for issue-page diagnostics, coding-agent handoff, and GitHub web-based resolution.
- The `Troubleshooter` and `Issue Coordinator` agent specs under `/.github/agents/` are kept for Copilot because they support structured orchestration and issue workflow handoff.
- Other agents can still follow those files as procedural references.

## Mux-Specific Notes
- mux (this tool) discovers project skills from `.mux/skills/` first, then falls back to `.agents/skills/` — so the skills under `.agents/skills/` (see Primary Workflows) are already visible to mux without any extra setup.
- mux MCP servers are configured globally in `~/.mux/mcp.jsonc`, with optional repo overrides in `./.mux/mcp.jsonc`. This repo's `.mux/mcp.jsonc` mirrors the cluster-facing servers from `.vscode/mcp.json` (`kubernetes`, `flux-operator-mcp`, `grafana`) so mux agents get the same Kubernetes/Flux/Grafana tools as VS Code/Copilot. `context7` and `tavily` are already configured globally for mux and are intentionally **not** duplicated in the repo override.
- If you add or change a server in `.vscode/mcp.json`, mirror the equivalent entry in `.mux/mcp.jsonc` (and vice versa) so both hosts stay in sync.

## Commit and Pull Request Guidelines
- Before committing, run the render/lint commands in "Essential Commands" for anything you touched (at minimum `kustomize build` on the affected app/overlay, plus `yamllint` on changed YAML).
- Commit messages follow **Conventional Commits**: `type(scope): summary` (e.g. `fix(monitoring): expose Grafana Service on port 443`, `feat(external-dns): add ExternalDNS for private domain`). Common types in this repo: `feat`, `fix`, `chore`, `docs`, `build`. Scope is usually the app/component directory name.
- There is no PR template; describe **what changed and why**, list the validation commands you ran, and call out any secret rotation or dependency-ordering implications (controllers before workloads).
- Never include plaintext secret values in commit messages or PR descriptions.

## Key References
- `/docs/README.md`
- `/docs/standards/repository-structure.md`
- `/docs/runbooks/add-application.md`
- `/docs/security/secret-management.md`
- `/docs/troubleshooting/web-troubleshooting.md`
- `/.github/copilot-instructions.md`
