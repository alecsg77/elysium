# VolSync controller

VolSync provides the shared PVC backup and restore API used by applications in
this repository. Workload-specific `ReplicationSource` and
`ReplicationDestination` resources remain with the owning application; this
directory owns only the controller, CRDs, namespace, and metrics endpoint.

The chart manages the `volsync.backube` CRDs. Flux uses `Create` during install
and `CreateReplace` during upgrades so schema changes are reconciled with the
controller release. Review CRD compatibility and the upstream release notes
before changing the pinned chart version.

See [Backup and restore](../../../docs/runbooks/backup-and-restore.md) for the
repository contract and onboarding procedure.
