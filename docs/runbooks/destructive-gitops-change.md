# Destructive GitOps change procedure

## Purpose

Flux pruning intentionally removes resources that disappear from reconciled source.
This runbook reduces accidental data or recovery-access loss by relying on runtime
retention annotations rather than a CI diff classifier.

Use it for a removal or destructive change involving a namespace, persistent volume,
PVC, backup repository, recovery-access binding, or other resource annotated with
`kustomize.toolkit.fluxcd.io/prune: disabled` or
`helm.sh/resource-policy: keep`.

## Preconditions

- Work from a branch through a PR; never update `main` directly.
- Identify the resource's owner and the applicable Flux, Helm, Kubernetes, or
  storage retention behavior.
- For persistent data, confirm a real backup and a documented, exercised restore
  procedure. Do not make a destructive storage change without that evidence.
- For access-plane changes, confirm a surviving administrator path independent of
  the resource being changed.
- Record the known-good Git revision and rollback procedure in the PR description.

## Two-PR sequence

### PR 1 — remove only the runtime protection

Remove the applicable `prune: disabled`, Helm keep annotation, or equivalent
retention setting while leaving the resource itself in source. Validate the affected
render locally, receive normal approval, and let Flux reconcile successfully. Confirm
the resource remains Ready and that the planned rollback revision is available.

### PR 2 — perform the removal or destructive change

Only after PR 1 has reconciled cleanly, remove or modify the resource. For persistent
data, verify the backup immediately before merging. After reconciliation, inspect the
affected Flux Kustomization, workload, PVC/PV, and any recovery-access path from the
surviving administrator route.

The root bootstrap composition and `clusters/kyrion/kustomization.yaml` remain
high-impact ownership boundaries. Do not remove or restructure them as routine
cleanup; use a separately approved recovery design.

## Validation

Before enabling auto-merge:

1. Render every affected Kustomize or Flux target locally.
2. Run `PR Validate Simple / validate` and inspect its GitOps/schema result when
   manifests changed.
3. Verify backup/restore evidence for persistent data and the surviving access path
   for recovery-plane changes.
4. After Flux reconciles, confirm the affected Kustomization and workload are Ready.
   Do not delete live Kubernetes resources to force a result.

## Rollback

Revert through a new PR and native squash auto-merge. Restore source from its
known-good Git revision; restore persistent data only through the tested backup
procedure. Do not manually delete Flux CRDs, Namespaces, or Secrets as a shortcut.

## Related documentation

- [Pull-request-only merge policy](../ci/merge-and-automerge-policy.md)
- [Backup and restore](backup-and-restore.md)
- [HelmRelease recovery](helm-release-recovery.md)
