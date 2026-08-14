# Paperclip

This catalog entry installs Paperclip with a dedicated Bitnami PostgreSQL release.
The database chart follows compatible `18.x` updates; a chart-major upgrade requires
an explicit backup-gated change. Flux Operator ResourceSet automation tracks the
upstream `latest` Paperclip tag by immutable digest and owns only the generated
`paperclip-image-auto` ConfigMap.

The `ai` overlay supplies two namespace-bound SealedSecrets:

- `paperclip-db-auth` provides PostgreSQL's native `password` and
  `postgres-password` keys.
- `paperclip-secrets` provides Paperclip's database connection URL and runtime
  authentication secrets.

Paperclip state is persisted at `/paperclip`; the database is persisted by the
`paperclip-db-postgresql` release. Both PVCs use Helm's `resource-policy: keep`
annotation so a release uninstall does not delete persistent data; PostgreSQL also
sets Kubernetes StatefulSet PVC retention to `Retain` for scale-down and deletion.
They are still backup-required: issue #90 tracks the required off-cluster backup and
restore contract. Before a destructive storage change or chart-major upgrade, verify
a recorded restore drill and use a Git revert/new PR for rollback rather than deleting
PVCs.
