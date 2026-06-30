---
name: 'review-gitops-config'
description: 'Review Kubernetes manifests, HelmRelease values, Flux resources, and Kustomize overlays in this repository. Use when asked to review GitOps config, inspect YAML changes, audit manifests, or check Flux and security best practices.'
---

# Review GitOps Config

## When To Use
- Use this skill for repository reviews of YAML, HelmRelease, Kustomization, or cluster config changes.
- Use it for pre-merge or pre-commit review requests focused on correctness, security, and regressions.

## Review Priorities
1. Security and plaintext secret exposure.
2. Flux dependency ordering and reconciliation behavior.
3. Kubernetes validity, resource safety, and health checks.
4. Helm values correctness and pinned versions.
5. Kustomize overlay hygiene and environment separation.
6. Missing validation or testing steps.

## Output Rules
- Findings first, ordered by severity.
- Focus on bugs, risks, regressions, and missing validation.
- Keep summaries short and secondary.

## References
- `.github/instructions/security.instructions.md`
- `.github/instructions/flux.instructions.md`
- `.github/instructions/helm.instructions.md`
- `.github/instructions/kubernetes.instructions.md`
- `.github/instructions/kustomize.instructions.md`