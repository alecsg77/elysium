# Pull-request validation

`PR Validate Simple / validate` is the repository's single required pull-request
check. It is a small `pull_request` workflow: the token is read-only, checkout
credentials do not persist, and it receives no repository or environment secrets,
kubeconfig, or cluster access.

The workflow deliberately treats a pull request as reviewable homelab configuration,
not hostile code. A contributor can change the workflow in the same PR; that risk is
accepted in exchange for a simple, maintained validation path, and is bounded by the
read-only token, no privileged credentials, and human approval of the current diff.

## What the check runs

These checks run on every pull request:

| Check | Purpose |
| --- | --- |
| `yamllint .` | YAML syntax and repository formatting policy. |
| Gitleaks | Detects secrets in the pull-request diff using `.gitleaks.toml`. |
| Plaintext Secret guard | Rejects changed YAML `kind: Secret` manifests under GitOps and Fission paths, except for the verified service-account-token scaffold described below. |

Additional checks are selected from the pull-request file list:

| Changed path | Additional validation |
| --- | --- |
| `apps/`, `clusters/`, `infrastructure/`, `monitoring/`, `.github/schemas/` | Build `clusters/kyrion/`; render the five Flux apply surfaces; validate each with strict kubeconform using Kubernetes defaults, local schemas, and the commit-pinned CRD catalog. |
| `charts/` | `helm lint` and `helm unittest` for `charts/cron-job` and `charts/onechart`. |
| `coder/templates/` | `terraform fmt -check`, `init -backend=false`, and `validate` for every current template root. |
| `.github/workflows/`, `scripts/` | actionlint plus shell syntax checks. |

The five Flux surfaces are `apps`, `infra-controllers`, `infra-configs`,
`monitoring-controllers`, and `monitoring-configs`. The aggregate `apps/base` catalog
is intentionally not rendered: some base HelmRelease names collide before an overlay
assigns namespaces.

Fission specifications receive the always-on YAML and Secret checks. There is no
separate policy engine or cluster-backed Fission validation in the required check.

## Secret handling

Plain Kubernetes `Secret` manifests are not permitted in GitOps or Fission source.
The only exception is
`infrastructure/configs/ci/copilot-agent-rbac/secret.yaml`, which must remain a
`kubernetes.io/service-account-token` scaffold with the verified name, namespace, and
service-account annotation and without `data` or `stringData`.

`.gitleaks.toml` permits a complete Bitnami SealedSecret ciphertext-shaped scalar
line. Gitleaks evaluates lines rather than YAML structure, so a deliberately crafted
plaintext value with exactly that shape is an accepted narrow residual risk. Ordinary
plaintext adjacent to ciphertext remains scanned. The tracked
`apps/base/coder/secret.yaml` is historical plaintext-Secret debt: do not change it
until its credential has been rotated and migrated to a SealedSecret or native Secret
reference.

## Runtime protection for destructive changes

The CI check is not a resource-diff policy engine. High-impact data, namespace, and
recovery-access resources instead use Flux/Kubernetes/Helm retention annotations.
Those annotations can leave intentionally removed resources orphaned; this is a
conscious tradeoff against automatic loss of data or access.

Follow [Destructive GitOps changes](../runbooks/destructive-gitops-change.md): first
remove the applicable runtime protection in one healthy PR and allow Flux to
reconcile, then make the removal or destructive change in a later PR. Backup and
restore evidence remains an operational requirement for persistent data.

## What a green check means—and does not mean

A green check means the selected source validation, Flux/Kustomize rendering, and
Kubernetes schema validation completed successfully. It does **not** certify:

- production-grade hardening or a generic Kubernetes security posture;
- remote Helm chart rendering or runtime behavior of a HelmRelease;
- successful Flux reconciliation in the cluster;
- application-level tests, backup restore drills, Sealed Secrets key recovery, or
  out-of-band administrator access.

Use Flux status and the relevant application/runbook checks after merge for those
operational guarantees.

## Local equivalents

Run the smallest applicable set before opening a PR:

```bash
yamllint .
kustomize build clusters/kyrion/
flux build kustomization apps --path clusters/kyrion --dry-run
flux build kustomization infra-controllers --path clusters/kyrion --dry-run
flux build kustomization infra-configs --path clusters/kyrion --dry-run
flux build kustomization monitoring-controllers --path clusters/kyrion --dry-run
flux build kustomization monitoring-configs --path clusters/kyrion --dry-run
helm lint charts/cron-job
helm lint charts/onechart
helm unittest charts/cron-job
helm unittest charts/onechart
actionlint .github/workflows/pr-validate-simple.yml
```

For a changed Coder template, run `terraform fmt -check -recursive`,
`terraform init -backend=false`, and `terraform validate -no-color` in the template
directory. The workflow verifies the local schema checksum before kubeconform and
fails when a rendered resource has no schema; do not add `-ignore-missing-schemas`.
