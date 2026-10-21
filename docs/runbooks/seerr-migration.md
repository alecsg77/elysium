# Overseerr to Seerr migration

Seerr's manifests live in `apps/base/seerr/seerr.yaml`, with environment values in `apps/kyrion/arkham/seerr-values.yaml`. The HelmRelease, Helm release and values ConfigMap are named `seerr`, `seerr` and `seerr-helm-values`. Seerr mounts `seerr/config` from the existing `pvc-storage` claim at `/app/config`, runs as UID/GID 1000, and migrates the copied Overseerr data on first startup. The existing ingress hostname is retained.

The approved sequence accepts downtime: uninstall Overseerr without deleting its data, copy `overseerr/config` to `seerr/config`, then deploy Seerr. The Arkham overlay initially suspends the **new** Seerr HelmRelease. This is a deliberate activation gate, not a suspended Overseerr release: suspending Overseerr would leave its Pod running. Keep `overseerr/config` unchanged as an additional rollback copy; never run both versions against the same directory.

LinuxServer.io [deprecated its Overseerr image](https://info.linuxserver.io/issues/2026-02-16-overseerr/) and recommends the official Seerr image. No maintained LinuxServer Seerr image was found at the time of this change; check again before any future image switch. The Seerr tag is pinned: Overseerr's ImagePolicy and automation markers were removed to prevent unreviewed updates during migration.

## Before merging the removal/preparation change

**Do not remove Overseerr until a recoverable, pre-migration backup has been verified. Do not activate Seerr until the stopped-data copy has also passed verification.** Do not infer recoverability from manifests or the presence of a backup PVC alone; the dated evidence below records the checks actually performed. Follow the [backup and restore contract](backup-and-restore.md): record data classification, RPO/RTO, backup destination and retention, successful backup/check and an isolated restore with SQLite integrity and settings validation. PVC retention is not a backup. Keep restored settings and credentials out of Git.

Arkham already has a separate `pvc-backups` volume used by other applications. A one-off backup can mount the `overseerr/config` subPath from `pvc-storage` read-only and save to a dedicated `overseerr/` directory on `pvc-backups`. While Overseerr is running, use SQLite's online backup API for `db/db.sqlite3`; **never** copy its live database/WAL files with ordinary filesystem `cp`. Copy `settings.json` and other configuration, excluding optional logs/cache, and verify the copied database with `PRAGMA integrity_check` and the settings file as JSON. Independently restore a copy into isolated scratch storage, comparing file checksums and opening the restored database. Do not restore over production as a test. This volume is local and shares the cluster's failure domain: it is a migration rollback copy, not an off-cluster disaster-recovery backup. Refresh it immediately before cutover if the source data may have changed since the last copy. Verify that the previous pinned image `lscr.io/linuxserver/overseerr:version-v1.35.0` remains available for rollback; LinuxServer no longer publishes moving tags.

Migration backup evidence:

- 2026-10-04 UTC: a one-off online backup completed while Overseerr remained running. A separate Job restored it to an isolated `emptyDir` and verified checksums, SQLite integrity, database tables and valid settings JSON.
- 2026-10-21 UTC, after a reported backup-drive incident: the previous backup passed the isolated recovery checks again. A fresh online backup completed at 20:54:10 UTC (three files, 387932 bytes), with matching checksums, SQLite integrity, valid settings JSON and unchanged source settings during the copy. The previous backup was retained. Temporary Jobs were removed; both backups remain on the PVC.

This verifies file-level recovery, **not** a full application startup, physical disk health or off-cluster recovery. Refresh the backup immediately before migration if Overseerr data changes.

Confirm UID/GID 1000 can read and write the existing config directory. Correct ownership only within the app's subdirectory if needed, never recursively across the shared PVC.

## Staged cutover

The removal/preparation PR and the later activation PR are separate GitOps states. Do not combine them into an immediately active replacement: Flux does not guarantee that the old Helm release has finished uninstalling before it starts reconciling the new release. No ordering assumption or automatic filesystem copy is hidden in the chart.

### 1. Remove Overseerr, preserve storage, prepare suspended Seerr

Merge the removal/preparation PR only after normal approval and successful validation. Flux prunes the old `overseerr` HelmRelease, which uninstalls its Helm release. It also removes the legacy values ConfigMap and image automation resources. The replacement `seerr` HelmRelease and `seerr-helm-values` ConfigMap are created, but the overlay patch sets `spec.suspend: true`, so no Seerr workload is installed yet.

The existing shared PVC/PV and their retention annotations are unchanged. The chart references `existingClaim: pvc-storage` and does not own or delete that claim. This is not a request to remove PVC/PV protection.

Before copying, verify all of the following:

- Flux has applied the intended removal/preparation revision.
- `HelmRelease/overseerr` is completely absent, not just terminating; its Helm uninstall succeeded.
- No Overseerr Deployment, ReplicaSet or Pod remains, including terminating Pods or another writer to `overseerr/config`.
- `HelmRelease/seerr` is suspended and no Seerr Deployment or Pod exists.
- The shared PVC remains Bound and `overseerr/config` is readable.

The apps Kustomization uses `wait: false`; a Ready Kustomization alone is **not** proof that Helm uninstall and Pod termination have completed. If any check fails, keep Seerr suspended and resolve it before proceeding. Downtime starts when Overseerr stops and lasts through copying and activation.

### 2. Copy stopped data, without moving or overwriting the original

Use an explicitly authorized, one-off operator copy Job; no temporary backup/copy workload is committed as a permanent application resource. Do not copy while either application is running. The Job must have no service-account token, run as UID/GID 1000 with dropped capabilities, and avoid `fsGroup` ownership changes on the shared claim. Mount the source subPath read-only. Any writable mount needed to create the destination must be used only for `seerr/`; never modify the source or other applications' directories.

1. Confirm free space and that `seerr/config` does not already exist, even as a symlink. If it exists, stop and inspect it; never merge into it, delete it or overwrite it automatically.
2. Create a private staging directory under `seerr/` on the same PVC. Copy the configuration into it, preserving file modes. Exclude only optional top-level logs/cache; do not follow symlinks and fail on unexpected symlinks or special files in configuration data. Copy the SQLite database **and any remaining WAL/SHM sidecars** together from the stopped application. Do not copy only the main database file if a WAL exists.
3. Compare file inventories, sizes and checksums against the source before opening the destination database. Verify required settings and database files, UID/GID 1000 access and valid settings JSON. Open the copied database using SQLite's normal WAL-aware mode, require `PRAGMA integrity_check` to return `ok`, and close it cleanly; do not use immutable mode if a WAL remains. Do not log settings, credentials or database contents.
4. Recheck that the source files have not changed during the copy. Only after all checks pass, finalize the staging copy as `seerr/config` without replacing any existing destination. Preserve the untouched `overseerr/config` and the independent pre-migration backup. Remove the temporary Job after recording redacted verification evidence privately.

This creates an additional local rollback copy, not an independent-disk or off-cluster backup. Retain the original directory and pre-migration backups until the migration has been accepted; their deletion is outside this change. The stopped copy avoids losing writes during the cutover, but the historical backup can be older. Failed verification leaves Seerr suspended and must not be bypassed.

### 3. Deploy Seerr through a follow-up activation PR

Only after stages 1 and 2 have been verified, open a small activation PR removing the Seerr suspension patch from `apps/kyrion/arkham/kustomization.yaml` (restore `patches: []` if it is the only patch). Do not imperatively resume the HelmRelease or activate it before the copied directory is ready. This migration PR intentionally stops at the suspension gate; it does not claim the application is deployed.

Render the chart and the base/overlay Kustomize builds. Verify the HelmRelease, Helm release, Deployment, Service and Ingress use `seerr`, the generated values ConfigMap is `seerr-helm-values`, and the Deployment uses one replica, Recreate, `seerr/config` mounted at `/app/config`, UID/GID 1000 and a startup probe. Confirm the previous hostname remains unchanged. After approval and Flux reconciliation, verify migration logs, health, access URL, sign-in, users, requests, media integrations and notifications. Do not publish private identifiers from logs or settings.

## Rollback

If copying fails before activation, keep Seerr suspended; the original Overseerr data has not been modified. Reintroduce the original Overseerr manifests and values through a reviewed Git change using the known-good pre-migration revision recorded in the PR.

If Seerr startup fails or data is missing, remove the Seerr HelmRelease through GitOps and wait for its uninstall and Pods to finish before restoring Overseerr through a reviewed Git change. Preserve the failed `seerr/config` for diagnosis; point Overseerr at its untouched `overseerr/config` using the previous pinned image. Do not point the old binary at the migrated Seerr copy. If the original is unavailable, restore the independently verified **pre-migration** backup before restarting Overseerr. Requests made after Seerr activation are not present in the original rollback copy and need separate reconciliation.

Leave all PVCs, PVs, original data and retention annotations intact. For a later protected-resource removal, follow [destructive GitOps change](destructive-gitops-change.md).

References: [Seerr migration guide](https://docs.seerr.dev/migration-guide), [Seerr backups](https://docs.seerr.dev/using-seerr/backups/).
