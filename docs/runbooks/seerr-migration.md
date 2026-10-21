# Overseerr to Seerr migration

The `overseerr` HelmRelease runs Seerr but deliberately retains its Kubernetes identity, `pvc-storage` claim, `overseerr/config` subPath, and ingress. The official image reads configuration at `/app/config`, runs as UID/GID 1000, and migrates Overseerr data on first startup. Do not run both versions against the same directory.

LinuxServer.io [deprecated its Overseerr image](https://info.linuxserver.io/issues/2026-02-16-overseerr/) and recommends the official Seerr image. No maintained LinuxServer Seerr image was found at the time of this change; check again before any future image switch. The Seerr tag is pinned: Overseerr's ImagePolicy and automation markers were removed to prevent unreviewed updates during migration.

## Before merging the image change

**Do not merge or reconcile the new image until a recoverable, pre-migration backup has been verified.** Do not infer recoverability from manifests or the presence of a backup PVC alone; the dated evidence below records the checks actually performed. Follow the [backup and restore contract](backup-and-restore.md): record data classification, RPO/RTO, backup destination and retention, successful backup/check and an isolated restore with SQLite integrity and settings validation. PVC retention is not a backup. Keep restored settings and credentials out of Git.

Arkham already has a separate `pvc-backups` volume used by other applications. A one-off backup can mount the `overseerr/config` subPath from `pvc-storage` read-only and save to a dedicated `overseerr/` directory on `pvc-backups`. While Overseerr is running, use SQLite's online backup API for `db/db.sqlite3`; **never** copy its live database/WAL files with ordinary filesystem `cp`. Copy `settings.json` and other configuration, excluding optional logs/cache, and verify the copied database with `PRAGMA integrity_check` and the settings file as JSON. Independently restore a copy into isolated scratch storage, comparing file checksums and opening the restored database. Do not restore over production as a test. This volume is local and shares the cluster's failure domain: it is a migration rollback copy, not an off-cluster disaster-recovery backup. Refresh it immediately before cutover if the source data may have changed since the last copy. Verify that the previous pinned image `lscr.io/linuxserver/overseerr:version-v1.35.0` remains available for rollback; LinuxServer no longer publishes moving tags.

Migration backup evidence:

- 2026-10-04 UTC: a one-off online backup completed while Overseerr remained running. A separate Job restored it to an isolated `emptyDir` and verified checksums, SQLite integrity, database tables and valid settings JSON.
- 2026-10-21 UTC, after a reported backup-drive incident: the previous backup passed the isolated recovery checks again. A fresh online backup completed at 20:54:10 UTC (three files, 387932 bytes), with matching checksums, SQLite integrity, valid settings JSON and unchanged source settings during the copy. The previous backup was retained. Temporary Jobs were removed; both backups remain on the PVC.

This verifies file-level recovery, **not** a full application startup, physical disk health or off-cluster recovery. Refresh the backup immediately before migration if Overseerr data changes.

Confirm UID/GID 1000 can read and write the existing config directory. Correct ownership only within the app's subdirectory if needed, never recursively across the shared PVC.

## Cutover and rollback

Render the chart and the base/overlay Kustomize builds. Verify the Deployment uses one replica, Recreate, the unchanged `overseerr/config` subPath mounted at `/app/config`, UID/GID 1000 and a startup probe. Reconcile only through GitOps. Confirm migration logs, health, access URL, sign-in, users, requests, media integrations and notifications. Do not publish private identifiers from logs or settings.

If migration fails or data is missing, stop Seerr through GitOps and preserve diagnostic state outside Git. Restore the verified **pre-migration** config and SQLite database, then revert the HelmRelease through a reviewed Git change and start the old image. Reverting the image alone is insufficient: the old binary may not understand migrated data. Leave the PVC, PV and retention annotations intact. For a later resource rename/removal, follow [destructive GitOps change](destructive-gitops-change.md).

References: [Seerr migration guide](https://docs.seerr.dev/migration-guide), [Seerr backups](https://docs.seerr.dev/using-seerr/backups/).
