# Backup, restore, and out-of-band recovery contract

> **Status: design and verification work is tracked in issue #90.** This runbook
> intentionally does not claim that a local PVC named `pvc-backups` is an
> off-cluster backup or that any restore drill has completed.

## Required contract before an R2 data change

For every persistent workload, record:

- classification: ephemeral, reconstructible, or backup-required;
- owner and data location;
- RPO and RTO;
- encrypted off-cluster destination and retention;
- backup command/automation and monitoring;
- restore command and validation;
- date and result of the last restore drill.

The initial inventory must cover Sealed Secrets key material, tsidp state,
application databases/PVCs, Arkham local PVs, Coder/RomM state, and monitoring
data. The exact host and storage endpoint details stay in local operational
documentation, not in this public repository.

## Sealed Secrets key backup

The Sealed Secrets private key is needed to decrypt every committed
`SealedSecret`. Export it only to a controlled temporary directory, encrypt it
before any persistent write, verify the encrypted artifact can be decrypted by an
authorized custodian, and securely remove the plaintext temporary export.

Do not commit the export, its passphrase, or the encrypted backup into this
repository. Follow the updated procedure in [Secret Management](../security/secret-management.md).

## Out-of-band recovery

Before relying on a Tailscale-managed access route, verify a recovery path that
does not depend on the Kubernetes Tailscale Operator. Record the test date,
operator, and outcome in the private operational log. Keep console/LAN/host
identifiers and credentials outside Git.

## Detection and post-merge audit

The repository includes two detective controls that complement the preventive
ruleset and trusted-base guard:

- `.github/workflows/audit-main-integrity.yml` fails when a new `main` commit has
  no GitHub pull-request association.
- `monitoring/configs/flux-safety-rules.yaml` alerts for non-ready bootstrap
  Kustomizations/critical HelmReleases and a reduced Flux/Tailscale recovery
  inventory.

Treat either signal as an incident. Preserve the current Git revision, inspect
Flux status through a surviving administrative path, and use [Destructive GitOps
Changes](destructive-gitops-change.md) or [GitHub Merge-Control
Break-Glass](github-break-glass.md) as appropriate. These controls cannot prove
an out-of-band channel exists: the channel's test date, operator, and result must
remain in the private operational log.

## Restore drill

A restore drill must be carried out before any destructive storage migration:

1. Restore a representative backup into an isolated target or approved recovery
   window.
2. Validate application integrity and access without exposing secrets in logs.
3. Measure actual recovery time and compare it with the workload RTO.
4. Record gaps, rotate exposed credentials if applicable, and update the contract.

## Related documentation

- [Secret Management](../security/secret-management.md)
- [Destructive GitOps changes](destructive-gitops-change.md)
- [HelmRelease recovery](helm-release-recovery.md)
