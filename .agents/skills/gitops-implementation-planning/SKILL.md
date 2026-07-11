---
name: 'gitops-implementation-planning'
description: 'Create implementation plans for new applications, infrastructure changes, refactors, or rollout work in this GitOps repository. Use when the user asks for a plan, architecture impact, sequencing, dependencies, validation, or rollback steps before implementation.'
---

# GitOps Implementation Planning

## When To Use
- Use this skill for planning before making GitOps changes.
- Use it for new app deployment, infrastructure changes, migrations, refactors, and rollout plans.

## Output Structure
- Overview
- Requirements
- Architecture impact
- Ordered implementation steps
- Validation and testing plan
- Rollback plan
- Documentation updates
- Security considerations

## Planning Rules
- Respect base/overlay separation and Flux dependency ordering.
- Identify CRD, controller, secret, ingress, storage, and monitoring prerequisites early.
- Prefer official charts or upstream deployment guidance before generic wrappers.
- Include concrete validation commands and explicit rollback conditions.

## References
- `/docs/runbooks/add-application.md`
- `/docs/standards/repository-structure.md`
- `.github/instructions/flux.instructions.md`
- `.github/instructions/helm.instructions.md`
- `.github/instructions/testing.instructions.md`