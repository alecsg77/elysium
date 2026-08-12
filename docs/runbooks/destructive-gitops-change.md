# Destructive GitOps change procedure

## Purpose

Flux pruning is intentional: a resource removed from a reconciled source can be
removed from the cluster. This procedure prevents an accidental source or
ownership change from becoming an unreviewed destructive action.

Use it whenever `PR Gate / required` classifies a proposal as **R2**, including a
critical resource deletion/rename, a PVC identity/storage change, or a change to
a protected Flux path, source, pruning, deletion policy, or dependency boundary.

## Preconditions

- The change is made on a branch and proposed by PR; never directly on `main`.
- The target resource appears in `.github/critical-resources.yaml`.
- Backup and rollback evidence is real, non-secret, and refers to a documented
  artefact or known-good Git revision.
- For persistent data, the backup/restore contract in issue #90 has been
  completed and the restore has been exercised. Until then, do not make an R2
  storage change.

## Two-PR R2 sequence

### PR 1 — declare intent / remove protection when required

Create `.github/critical-removal-intents/<resource-id-with-slashes-as-__>.yaml`:

```yaml
resource: tailscale/connector
operation: remove
backup: "Not applicable: Connector has no persistent data; see recovery commit <sha>."
rollback: "Restore connector.yaml from commit <sha>."
```

Use `operation: remove` when the later PR deletes a critical resource. For a
protected R2 field change that retains the resource—such as a CRD schema or PVC
storage field—use `operation: change` and make the backup/rollback evidence
specific to that change.

For resources carrying `kustomize.toolkit.fluxcd.io/prune: disabled`, a removal
preparation PR also removes that annotation. It does **not** remove the resource.
Let native auto-merge complete only after `PR Gate / required` succeeds.

### PR 2 — consume intent and perform the exact R2 operation

In a later branch/PR, remove the intent file and perform exactly its matching
R2 operation. For `remove`, delete the target resource too; for `change`, modify
the intended protected resource. The trusted-base guard reports every protected
field that changed, compares the already-merged intent against the policy, and
consumes it so it cannot authorize a future unrelated operation.

The five root bootstrap files and the fixed `clusters/kyrion/kustomization.yaml`
resource list are never removable through this procedure. Escalate those cases to
a separately approved recovery design.

## Validation

Before enabling auto-merge:

1. Render every affected Kustomize/Flux target locally.
2. Confirm the critical guard shows the expected R2 operation and no unexpected
   resource identities disappear.
3. For access-plane changes, use the documented non-sensitive validation from a
   surviving administrative path.
4. For data changes, verify the backup exists and the documented restore has been
   tested before the production change.
5. After reconciliation, check the affected Flux Kustomization and workload are
   Ready; do not delete live Kubernetes resources to force a result.

## Rollback

Revert the merged PR through a new PR and use native auto-merge. Restore a
resource from its documented known-good Git revision; restore persistent data
only through its tested backup procedure. Do not manually delete Flux CRDs,
Namespaces, or Secrets as a shortcut.

## Related documentation

- [Pull-request-only merge policy](../ci/merge-and-automerge-policy.md)
- [Backup and restore](backup-and-restore.md)
- [HelmRelease recovery](helm-release-recovery.md)
