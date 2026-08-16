# Backup and restore

This runbook defines the reusable backup and restore contract for persistent
applications. VolSync provides the Kubernetes API and Restic provides
client-side encryption, retention, repository integrity, and object-storage
support. OpenClaw is the first workload adopting the contract; each additional
PVC uses the same resource shapes and operational gates.

## Recovery contract

The repository-wide baseline is:

| Objective | Baseline |
|---|---|
| Backup schedule | Every 6 hours |
| RPO | 24 hours |
| RTO for one application PVC | 2 hours |
| Retention | 4 hourly, 7 daily, 5 weekly, 12 monthly snapshots |
| Repository | One encrypted Restic repository path per PVC |
| Restore verification | At least quarterly and before a destructive migration |

An application may declare stricter objectives in its own documentation. A
less strict objective requires an explicit risk decision; it must not be
introduced by silently weakening the shared monitoring rules.

## Inventory and consistency tier

Before onboarding a workload, record all persistent state and choose one tier:

- **filesystem**: files can be copied while the application is running;
- **application-consistent**: the application exposes a supported flush,
  checkpoint, or backup hook;
- **stopped**: the workload must be stopped before the final backup.

`copyMethod: Direct` is the portable baseline for `local-path` PVCs because it
does not require CSI snapshots. It reads the mounted volume directly and does
not make a live database transactionally consistent. For SQLite, database
servers, or similar state, use an application hook or a stopped final backup
for destructive operations. Validate restored databases with their native
integrity tooling; file presence alone is not sufficient.

## Secret contract

Create one namespace-scoped Secret per protected PVC. The Secret name is
referenced by `spec.restic.repository` and contains the Restic variables needed
by the selected backend:

- `RESTIC_REPOSITORY` with a unique, non-sensitive repository path;
- `RESTIC_PASSWORD` with a unique encryption password;
- backend credentials such as `AWS_ACCESS_KEY_ID` and
  `AWS_SECRET_ACCESS_KEY` for an S3-compatible endpoint;
- optional backend settings required by Restic, such as region or endpoint.

Store only a SealedSecret in Git. Never reuse a repository path between PVCs,
print secret values in logs, or publish bucket names, private endpoints,
snapshot IDs, object keys, credentials, or encryption material. Keep a private
recovery copy of the repository password and backend credentials outside the
cluster; a SealedSecret alone is not a disaster-recovery copy because it is
tied to the cluster sealing key.

Use least-privilege backend credentials restricted to the workload repository
prefix. Rotate and revoke them after a suspected disclosure and after temporary
migration access is no longer required.

## Onboard a PVC

Keep the `ReplicationSource` with the application owner, not with the VolSync
controller. The reusable shape is:

```yaml
apiVersion: volsync.backube/v1alpha1
kind: ReplicationSource
metadata:
  name: <application>-backup
  namespace: <application-namespace>
spec:
  sourcePVC: <pvc-name>
  trigger:
    schedule: "0 */6 * * *"
  restic:
    copyMethod: Direct
    repository: <application>-restic
    pruneIntervalDays: 7
    retain:
      hourly: 4
      daily: 7
      weekly: 5
      monthly: 12
    moverResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 1
        memory: 1Gi
```

Confirm that the PVC, Secret, and `ReplicationSource` share a namespace. Render
the application base and cluster overlay before merging. After reconciliation,
wait for `status.lastSyncTime`, inspect `status.latestMoverStatus.result`, and
verify that the three generic VolSync alerts remain inactive. Do not treat the
resource being `Ready` as proof that recoverable data exists.

## Perform a restore drill

Never restore over the production PVC during a drill.

1. Select a known successful snapshot privately and record only its timestamp
   and redacted identifier in the evidence.
2. Create a scratch PVC in an isolated drill namespace with enough capacity.
3. Materialize the repository Secret in that namespace using a separately
   sealed copy of the same private values.
4. Create a temporary `ReplicationDestination` using `copyMethod: Direct`, the
   scratch PVC as `destinationPVC`, and a unique manual trigger value.
5. Wait until `status.lastManualSync` equals the trigger and the latest mover
   result is `Successful`.
6. Mount the restored PVC read-only in an offline validation Job. Disable
   service exposure and egress unless the validation itself requires a reviewed
   destination.
7. Verify required files, ownership, permissions, symlinks, and application
   invariants. Run native integrity checks for every restored database.
8. Record elapsed restore time against the RTO and publish only redacted
   evidence.
9. Remove the validation Job, `ReplicationDestination`, scratch PVC, and
   drill-only Secret through Git. Confirm their deletion before closing the
   drill.

The destination shape is:

```yaml
apiVersion: volsync.backube/v1alpha1
kind: ReplicationDestination
metadata:
  name: <application>-restore-drill
  namespace: <drill-namespace>
spec:
  trigger:
    manual: <unique-trigger>
  restic:
    copyMethod: Direct
    repository: <application>-restic
    destinationPVC: <scratch-pvc>
```

## Destructive-operation gate

Before deleting, replacing, migrating, or shrinking persistent storage, require
all of the following:

- a successful backup within the workload RPO;
- backend confirmation that encrypted objects exist off-cluster;
- a completed restore drill from the same repository and credential set;
- application-level integrity checks on the restored data;
- measured restore time within the RTO;
- a rollback owner and an explicit approval tied to the current Git revision.

If any item is missing, stop the destructive operation. A backup log without a
restore drill is not sufficient evidence.

## Evidence and incident response

Public evidence may include UTC start/end times, duration, byte/file counts,
high-level integrity results, RPO/RTO outcome, and redacted snapshot hashes. It
must exclude credentials, repository passwords, bucket or endpoint identifiers,
object keys, private domains, internal addresses, and restored application
content.

Alert response starts at the first failing control point: verify the
`ReplicationSource` status, then the mover Job and events, Secret key names
without values, PVC mount/scheduling, and finally backend reachability. Do not
run `restic unlock` or mutate repository state until an active writer has been
excluded and the action is approved.
