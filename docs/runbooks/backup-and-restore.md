# Backup, restore, and out-of-band recovery contract

> **Status: design and verification work is tracked in issue #90.** This runbook
> does not claim that a configured Schedule is a recoverable backup. That claim
> requires a successful backup, repository check, and restore drill.

## K8up and Restic baseline

K8up is the cluster backup operator and Restic is the repository format and
encryption engine used by the Jobs it creates. Restic does not require a
separate controller or installation. The baseline intentionally avoids object
storage, storage plugins, custom backup images, and repository wrapper scripts.

Each protected namespace receives:

- one dedicated directory below the private host backup root;
- one static local `PersistentVolume` with reclaim policy `Retain`;
- one namespace-scoped repository PVC;
- one namespace-scoped SealedSecret containing the Restic password;
- one or more K8up Schedules selecting only the intended workload PVCs.

The public repository uses placeholders for node names and host paths. Keep the
real mount path, filesystem UUID, node identity, capacity evidence, and preflight
results in the private operational log. A typical private layout is:

```text
<backup-root>/<namespace>
```

Do not share a repository directory between namespaces. For this single-admin
homelab, namespace repositories may reuse one cluster backup password to reduce
credential management. Seal the value independently into each namespace-scoped
Secret required by K8up.

The SealedSecret stored in Git is the recovery copy of the Restic password. This
accepted simplification depends on keeping an off-cluster backup of the complete
active Sealed Secrets key set. Refresh and retest that backup whenever a new
sealing certificate is adopted. A separate password-manager copy of the Restic
password is optional, not required by this recovery model.

The local external disk protects against loss of a workload PVC or its primary
disk. It does not protect against theft, fire, or a root compromise of the host.
This residual risk is acceptable for this homelab, but a local repository must
not be described as an off-site backup.

## Recovery objectives and retention

The shared baseline is:

| Objective | Baseline |
|---|---|
| Backup schedule | Every 6 hours |
| Maximum accepted backup age | 24 hours |
| Restore target | Within 2 hours |
| Retention | 4 hourly, 7 daily, 5 weekly, 12 monthly |
| Repository check | Weekly |
| Prune | Weekly, separated from the check window |

K8up's official ServiceMonitor and chart-managed rules cover failed Jobs, the
latest scheduled backup failing, and namespaces with an active Schedule but no
Job in the last 24 hours. They use only operator and kube-state-metrics data.
Detailed per-backup Restic metrics require a Pushgateway and are intentionally
not part of this baseline. A missing alert is not proof of recoverability;
verify the repository and perform restore drills.

## Trusted-host preflight

Before adding a local repository PV, verify from the host that the private
backup root is the intended filesystem, is mounted read-write, and has adequate
free space. Create only the namespace child directory with the reviewed owner,
group, and setgid permissions. Confirm with a disposable file that the UID and
supplemental GID used by K8up Jobs can create and remove repository data.

When the repository requires an additional group, use `supplementalGroups` in
K8up Pod security contexts. Do not use `fsGroup` for a Job that mounts an
application PVC: kubelet ownership handling can alter restored or source data
metadata and invalidate an otherwise successful drill.

Record the filesystem UUID and test result privately. Do not change the parent
directory, publish infrastructure identifiers, or merge the PV until this
preflight succeeds.

## Onboard a PVC

Keep K8up `Schedule` resources, repository PVCs, and SealedSecrets in the owning
application overlay. A Schedule must:

- select only the intended PVC label;
- mount the namespace repository PVC at the backend's local mount path;
- reference the Secret key `password` for Restic encryption;
- apply the shared retention, deadline, history, and resource limits;
- run backup, check, and prune in distinct reviewed windows.

Do not modify an application's existing PVC merely to onboard backup. After
reconciliation, verify that the repository PV and PVC are `Bound`, the Schedule
is ready, the backup Job succeeded, the expected PVC path has a snapshot, the
check completed, and the repository directory contains Restic data.

Live filesystem backup does not guarantee application consistency. Databases
and stateful applications must pass native integrity checks after restore. If a
restore exposes SQLite, configuration, permission, or startup errors, switch to
an application-aware or stopped backup; do not weaken the drill criteria.

## Restore drill

Never restore over a production PVC during a drill. Every drill resource is
created and removed through GitOps; do not use an imperative restore, PVC
mutation, or workload scale/restart.

### Stage 1: isolated restore target

Each OpenClaw drill stage creates one uniquely named temporary scratch PVC and
one K8up `Restore` targeting that claim. The Restore references the existing
repository PVC and password Secret without copying either one, selects
`/data/openclaw-home-pvc`, and writes only to the scratch claim. It intentionally
has no pinned snapshot ID or restore-time filter: K8up selects the latest
snapshot that contains the requested path.

The scratch PVC is deliberately not labelled `app: openclaw` and has the
`k8up.io/backup: "false"` opt-out, so it is neither a production mount nor a
new Schedule backup source. It is sized and configured independently of the
production claim, is temporary, and must be removed by a later cleanup PR.

After the stage-1 PR merges, wait for the Flux `apps` Kustomization to be Ready,
the scratch PVC to be `Bound`, and the Restore to report success within its
two-hour deadline. Confirm the generated K8up restore Job references only the
repository PVC and scratch PVC; do not collect or publish its logs, snapshot
identifier, restored content, repository path, or credentials. A failed Restore
must be handled by reverting the stage-1 GitOps change or correcting it in a
new scoped PR; production remains outside the restore target.

### Stage 2: direct isolated verification and cleanup

Only after Stage 1 has succeeded may an explicitly authorized operator create a
short-lived diagnostic Pod and use `exec` to inspect the scratch restore. The
Pod must carry the dedicated `restore-drill-diagnostic` label selected by the
GitOps-managed deny-all NetworkPolicy. It must mount only the scratch PVC
read-only, use an in-memory `emptyDir` for temporary files, and have no Service,
Ingress, production PVC, repository PVC, Secret, TLS material, or ServiceAccount
token. It runs as UID/GID 1000 with RuntimeDefault seccomp, a read-only root
filesystem, no privilege escalation, and all Linux capabilities dropped.

The direct diagnostic must emit only aggregate, redacted evidence: timestamps,
duration, file count, aggregate bytes, database count, symlink count, generic
check result, and an aggregate checksum. Do not collect or publish restored
names, paths, contents, credentials, repository details, or snapshot identifiers.
It must fail closed for special entries, unreadable data, unexpected layout or
ownership/modes, and unsafe symlinks. A relative symlink is allowed only when
its lexical target remains inside the scratch tree. An absolute symlink is
allowed only when it is under `/app`, the pinned OpenClaw image's application
root, and resolves to an existing directory beneath that root. Never traverse a
restored symlink.

The diagnostic parses the single restored `openclaw.json`, verifies the
application-home, workspace, and configuration metadata against the production
workload, runs `PRAGMA integrity_check` read-only for each detected SQLite
database, and runs `openclaw config validate` with the restored configuration and
a writable temporary home. It must not invoke `gateway run` or bind a listener.
No meaningful offline gateway-start/health check is established without mounting
production credentials and TLS material, which remain prohibited here.

After the direct evidence is recorded, delete the diagnostic Pod immediately and
confirm it is absent. Use read-only queries to confirm Flux `apps` is Ready, the
deny-all policy selected only the diagnostic Pod, the production OpenClaw
Deployment remains available with one replica, and its production PVC identity
is unchanged.

A completed K8up Restore never reruns after its spec changes. If restore behavior
needs correction, create a new named scratch PVC and Restore through GitOps;
never mutate or rerun the completed Restore imperatively. After the final direct
verification, a separate cleanup PR removes only the temporary diagnostic
NetworkPolicy, Restore, and scratch PVC. It preserves the K8up Schedule,
repository PV/PVC, repository password Secret, Restic data, production OpenClaw
Deployment/PVC/Secrets/TLS, and all unrelated resources.

## Operator-independent Restic recovery

The repository remains usable without K8up. On a trusted Linux host, mount the
external disk and recover the password from the Git-tracked SealedSecret with
the off-cluster sealing-key backup. Use `kubeseal --recovery-unseal` and write
the recovered value only to a mode-0600 temporary file; alternatively, restore
the key set into a replacement Sealed Secrets controller. Then use the standard
Restic CLI against the namespace repository:

```bash
export RESTIC_PASSWORD_FILE=<protected-password-file>
restic --repo <repository-path> snapshots
restic --repo <repository-path> check
restic --repo <repository-path> restore latest --target <temporary-restore-directory>
```

Run restore into a new temporary directory and apply the same integrity checks
as a Kubernetes drill. Do not put the password on the command line or run
`forget`, `prune`, `unlock`, or repository deletion as part of fallback
validation.

## Rollback K8up

Remove Schedules first and wait for active Jobs to finish. Preserve repository
PVs, PVCs, SealedSecrets, external password-manager entries, and all Restic
data. The PV reclaim policy must remain `Retain`.

Remove every K8up custom resource before uninstalling the operator. Verify the
repository with the Restic CLI before completing the rollback. Never automate
`restic forget`, manual prune, repository initialization, or directory deletion
during rollback.

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

## Related documentation

- [Secret Management](../security/secret-management.md)
- [Destructive GitOps changes](destructive-gitops-change.md)
- [HelmRelease recovery](helm-release-recovery.md)
