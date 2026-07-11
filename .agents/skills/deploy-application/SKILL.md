---
name: 'deploy-application'
description: 'Deploy a new application to this Flux GitOps cluster. Use when asked to add an app, scaffold base and overlay manifests, choose a Helm chart, wire ingress, or prepare deployment validation.'
---

# Deploy Application

## When To Use
- Use this skill for new application onboarding in this repository.
- Use it when the user wants a new HelmRelease, Kustomize app, or raw-manifest deployment.
- Do not use it for troubleshooting an existing failed deployment; use `troubleshoot-flux` or the `Troubleshooter` agent instead.

## Required Inputs
- Application name in kebab-case.
- Deployment method: HelmRelease, Kustomize, or raw manifests.
- Namespace strategy: new namespace or existing namespace.
- Ingress exposure: internal, external, or none.
- Secrets, storage, and dependency requirements.

## Workflow
1. Review file placement and chart-selection rules before proposing files.
2. Choose the deployment source using repository chart priorities.
3. Create the base layout in `apps/base/<app>/` with environment-agnostic resources only.
4. Create the environment-specific overlay changes in `apps/kyrion/`.
5. Plan sealed secrets, ConfigMaps, and values sources before wiring them into the manifests.
6. Validate with `kustomize build`, `flux build`, and `helm template` when applicable.

## Repository Rules
- Base resources live in `apps/base/<app>/`.
- Overlay-only patches and environment-specific resources live in `apps/kyrion/`.
- Pin chart versions and image tags explicitly.
- Never commit plaintext secrets.
- Prefer one resource per YAML file.

## Validation Gates
- `kustomize build apps/base/<app>/`
- `kustomize build apps/kyrion/`
- `flux build kustomization apps --path clusters/kyrion`
- `helm template <app> <chart> -f values.yaml` when using HelmRelease

## References
- `/docs/runbooks/add-application.md`
- `/docs/standards/repository-structure.md`
- `.github/instructions/flux.instructions.md`
- `.github/instructions/helm.instructions.md`
- `.github/instructions/kustomize.instructions.md`
- `.github/instructions/kubernetes.instructions.md`