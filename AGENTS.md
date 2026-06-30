# Elysium Agent Guide

Vendor-neutral operating guide for AI coding agents working in this repository.

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
- Respect the base/overlay split:
  - Base: `apps/base/<app>/`
  - Environment overlay: `apps/kyrion/`
- Respect Flux dependency ordering: controllers/CRDs before dependent resources.
- Keep documentation authoritative in `/docs`, not duplicated across agent files.

## Validation Expectations
- Validate YAML and rendered output before finalizing changes.
- Preferred checks:
  - `kustomize build apps/base/<app>/`
  - `kustomize build apps/kyrion/`
  - `flux build kustomization apps --path clusters/kyrion`
  - `helm template <name> <chart> -f values.yaml` when using HelmRelease
- For troubleshooting, prefer the smallest diagnostic command set that can identify the first failing control point.

## Cross-Agent Compatibility Rules
- Keep Copilot-specific files valid for Copilot first.
- For portability, prefer reusable guidance in `/docs`, `AGENTS.md`, `CLAUDE.md`, and plain markdown `SKILL.md` bodies.
- Treat `.github/skills/<name>/SKILL.md` as reusable workflow references even if your host does not natively support skills.
- Treat `.github/agents/*.agents.md` as role/workflow references if your host does not support custom agent frontmatter.

## Primary Workflows
- Deploy application: `.github/skills/deploy-application/SKILL.md`
- Manage sealed secrets: `.github/skills/manage-sealed-secrets/SKILL.md`
- Generate docs: `.github/skills/generate-gitops-docs/SKILL.md`
- Review GitOps config: `.github/skills/review-gitops-config/SKILL.md`
- Plan GitOps work: `.github/skills/gitops-implementation-planning/SKILL.md`
- Search historical incidents: `.github/skills/knowledge-base-search/SKILL.md`
- Troubleshoot Flux and Kubernetes issues: `.github/skills/troubleshoot-flux/SKILL.md`

## Copilot-Specific Workflows
- Copilot is the primary hosted workflow for issue-page diagnostics, coding-agent handoff, and GitHub web-based resolution.
- The `Troubleshooter` and `Issue Coordinator` agent specs under `/.github/agents/` are kept for Copilot because they support structured orchestration and issue workflow handoff.
- Other agents can still follow those files as procedural references.

## Key References
- `/docs/README.md`
- `/docs/standards/repository-structure.md`
- `/docs/runbooks/add-application.md`
- `/docs/security/secret-management.md`
- `/docs/troubleshooting/web-troubleshooting.md`
- `/.github/copilot-instructions.md`
