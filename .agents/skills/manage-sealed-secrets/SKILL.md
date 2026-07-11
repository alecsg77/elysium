---
name: 'manage-sealed-secrets'
description: 'Create, rotate, and wire Bitnami Sealed Secrets for this GitOps repository. Use when asked to add a secret, rotate credentials, seal secret values, or connect secret data to Flux and application manifests.'
---

# Manage Sealed Secrets

## When To Use
- Use this skill for any new or rotated secret committed to this repository.
- Use it when the user needs namespace-scoped application secrets or cluster-wide substitution values.
- Do not use it to share or inspect raw secret material in chat.

## Required Inputs
- Secret name and namespace.
- Secret type: generic, docker-registry, tls, or opaque.
- Target application or cluster-level consumer.
- Whether this is a new secret or a rotation.

## Workflow
1. Identify the consumer and the correct repository location for the sealed secret.
2. Choose the safest creation flow using `kubeseal` and `etc/certs/pub-sealed-secrets.pem`.
3. Add or update the sealed secret manifest.
4. Wire references through `valuesFrom`, `secretKeyRef`, or Flux substitution.
5. Validate decryption and consumer readiness after reconciliation.

## Repository Rules
- Never commit plaintext secrets.
- Prefer app-scoped sealed secrets near the application overlay or base where the repo conventions expect them.
- Use `clusters/kyrion/sealed-secrets.yaml` only for cluster-level substitution data.
- Recreate the sealed secret if the namespace changes.

## Validation Gates
- Confirm the secret manifest is referenced by the relevant kustomization.
- `kubectl get sealedsecret <name> -n <namespace>`
- `kubectl get secret <name> -n <namespace>` after reconciliation
- Validate the consuming workload or HelmRelease picks up the new value

## References
- `/docs/security/secret-management.md`
- `.github/instructions/security.instructions.md`
- `.github/instructions/flux.instructions.md`