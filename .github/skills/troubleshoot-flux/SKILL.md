---
name: 'troubleshoot-flux'
description: 'Troubleshoot Flux, HelmRelease, Kustomization, and Kubernetes deployment issues in this repository. Use when diagnosing failed reconciliation, pod errors, HelmRelease timeouts, variable substitution failures, or other GitOps deployment problems.'
---

# Troubleshoot Flux

## When To Use
- Use this skill for on-demand diagnostics of Flux or Kubernetes deployment failures.
- Use it when the user provides a failing resource, namespace, issue number, or error message.
- Prefer the `Troubleshooter` agent when the investigation needs a dedicated diagnostic mode, multi-stage issue workflow, or follow-on coordination handoff.

## Diagnostic Flow
1. Start from the most concrete anchor available.
2. Verify Flux health and identify the first failing control point.
3. Separate root cause from cascading symptoms.
4. Summarize evidence, likely cause, and the next corrective workflow.
5. When a GitHub issue workflow is needed, hand off to `Issue Coordinator` or use the documented web troubleshooting flow.

## Boundaries
- Stay read-only unless the user explicitly changes mode or asks for implementation.
- Redact secrets, tokens, kubeconfig data, and private network details.
- Prefer the smallest diagnostic snippet that proves the failure.

## References
- `/docs/troubleshooting/web-troubleshooting.md`
- `/docs/troubleshooting/known-issues.md`
- `/docs/security/secure-troubleshooting.md`
- `.github/instructions/flux.instructions.md`
- `.github/instructions/kubernetes.instructions.md`