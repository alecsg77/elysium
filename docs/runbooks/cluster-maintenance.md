# GitOps changes and direct cluster maintenance

## Purpose

Git defines the desired configuration. Direct operations inspect the running
system, trigger its controllers, or carry out bounded maintenance. Choose the
path by the effect of an operation, not its command name or how briefly a
resource will exist. This applies to CLI, MCP, scripts, and host-side tools alike.

A request to diagnose authorizes read-only inspection. A request to repair a
workload authorizes ordinary recovery operations within that scope. Destructive
data operations, schema migrations, production restores, and interruptions of
otherwise healthy stateful writers require explicit authorization covering that
operation and its recovery plan. Reuse authorization within its stated scope;
do not ask again for each command or retry.

## Decision table

| Operation | Path | Boundary |
| --- | --- | --- |
| Read status, events, metrics, or bounded logs; run read-only diagnostics | Direct | Protect credentials and private identifiers; diagnosis alone does not authorize repair. |
| Reconcile an existing Flux source, Kustomization, or HelmRelease; reset failed attempts; request a one-off Helm action through Flux | Direct | Use the configured sources and desired versions; these triggers do not authorize a new configuration or version. |
| Restart controller-owned workload pods or request a rollout restart | Direct recovery | Preserve the workload configuration and storage; do not delete unmanaged, retained, or recovery-access resources as a restart shortcut. |
| Temporarily suspend a narrowly scoped reconciler or stop/scale a writer for maintenance | Direct maintenance | Record the original settings, pause every controller that can undo the temporary change, and restore exactly those settings after maintenance. |
| Run a one-off native database migration, repair, backup, or restore | Direct maintenance | Obtain the required authorization; use a verified recovery point, the supported native tool, and the intended writer identity. Enforce one writer while the application is offline. |
| Create a short-lived diagnostic or maintenance Pod/Job and remove it afterwards | Direct maintenance | Meet the temporary-resource conditions below; do not use the resource to introduce a service or change security/storage configuration. |
| Change images, chart versions, commands, environment, probes, resource limits, normal replica counts, schedules, or application configuration | Git branch and PR, then Flux | Desired configuration remains in Git. Existing Git-declared image automation may update its declared outputs under its own documented contract. |
| Add or change Services, ingress, certificates, Secrets, RBAC, NetworkPolicies, controllers, CRDs, Flux sources/ownership, or namespaces | Git branch and PR, then Flux | A temporary name or expiry does not turn a security, access, ownership, or platform configuration change into maintenance. |
| Add, resize, rebind, replace, or delete a PV/PVC; change retention; uninstall a release or remove a managed workload | Git branch and PR, then Flux | Follow the destructive-change and backup/restore procedures, including any two-PR requirement. |
| Repeated repair required at every startup, scheduled operational work, or a lasting recovery workaround | Git branch and PR, then Flux | Recurring behavior is part of the desired configuration and needs a maintained owner. |

Operational reconcile/restart timestamps, status, controller-generated children,
and the authorized result of a native data migration are not declarative drift.
Changing a managed resource's functional spec or a Git-managed config file on a
PVC to keep a fix alive is drift and must be represented in Git. Manual Helm
install/upgrade/rollback, imperative image changes, and applying replacement
manifests to Flux-owned resources are not substitutes for a GitOps change.

## Temporary-resource conditions

A direct Pod/Job is allowed only when all of these conditions hold:

- It serves the current diagnostic or authorized maintenance task, has a unique
  name and operation label, and has no Git/Flux/Helm ownership or adoption labels.
- It is not added to a source inventory, scheduled, exposed through a Service or
  ingress, or left running after the operation. Jobs have a deadline and bounded
  retries; record and remove their Pods/Jobs after collecting redacted evidence.
- It uses an appropriate pinned image and the application's UID/GID for writes.
  Use no privileged mode, host namespace, added capabilities, new RBAC, or
  ServiceAccount token. Mount only the required volumes and existing credential
  references. Diagnostics mount application data read-only; write access is
  limited to the explicitly authorized repair or restore target.
- A writable production mount has no competing writer. The operation preserves
  the PVC/PV identity, storage binding, retention protections, and file ownership.
- It does not bypass a more specific procedure. In particular, the isolated
  restore-drill resource, network isolation, read-only diagnostic, and cleanup
  requirements in [Backup and restore](backup-and-restore.md) remain mandatory.

A disposable manifest can be kept in a protected temporary directory and used
with `kubectl create`; it need not be committed merely to be deleted in another
PR. Do not use `kubectl apply` to update a managed resource under this exception.

## Maintenance procedure

1. Identify the workload, its reconcilers, the known-good Git revision, exact
   resources/data affected, and the user's authorization. Keep private paths,
   device identifiers, credentials, and detailed recovery evidence outside Git.
2. Record the original suspend flags, replica settings, image digest, PVC/PV
   identities, and application state needed for rollback. Check for concurrent
   jobs or operators that can write to the same data. Do not begin if another
   controller or an unknown writer cannot be accounted for.
3. Before a data mutation, confirm the backup destination is the intended mounted
   filesystem, create or verify a sufficiently recent application-consistent
   backup, and verify recovery using the exercised restore procedure. A Bound
   repository PVC, a ready Schedule, or a local copy on the production volume
   alone is not recovery evidence. Apply the contract in
   [Backup and restore](backup-and-restore.md).
4. Suspend only the reconciler(s) needed to protect the maintenance window, stop
   the writer, and verify its processes/Pods have exited before mounting data
   read-write elsewhere. For a Helm-managed workload, account for both the
   HelmRelease and any parent Kustomization that can reset its suspend setting.
5. Run the supported native maintenance tool with the same compatible image and
   state paths. Check its exit code and native integrity/readiness results.
   On failure, preserve the backup and evidence; do not reset data or chain
   speculative repairs. Restore data only through the authorized restore plan.
6. Remove temporary resources, restore the exact recorded replica and suspend
   settings, resume the original reconcilers, and reconcile the Git revision.
   Do not resume a writer against unverified or partly migrated state; report
   the stopped condition and the remaining recovery action if rollback fails.
7. Verify Flux and application readiness, data integrity, and unchanged storage
   identities. Confirm no unintended spec/config drift or temporary resources
   remain. Record the redacted result in the task or private operational log;
   operation-specific artifacts do not require a Git commit.

If a lasting configuration defect is discovered, fix it through a PR. Do not
extend a maintenance suspension indefinitely to hide drift. Unknown scope or
missing backup/restore evidence is a reason to investigate or ask for the missing
information, not permission to guess.

## Examples

For an OpenClaw upgrade blocked on a session schema migration, an authorized
operator may stop the Gateway under a bounded reconciliation suspension, verify
a current recoverable backup, run the same digest-pinned image once with
`openclaw doctor --fix --non-interactive`, and restore normal reconciliation.
This does not require adding and later removing a migration init container in
Git. An init container that must run on every future startup is a GitOps change.

A PVC restore drill continues to use its documented GitOps scratch targets and
isolation controls. Deleting a PVC to make a failed application start is a
destructive configuration/data change, not a restart or maintenance operation.

## Related documentation

- [Repository structure](../standards/repository-structure.md)
- [Secure troubleshooting](../security/secure-troubleshooting.md)
- [Destructive GitOps changes](destructive-gitops-change.md)
- [HelmRelease recovery](helm-release-recovery.md)
- [Merge and auto-merge policy](../ci/merge-and-automerge-policy.md)
