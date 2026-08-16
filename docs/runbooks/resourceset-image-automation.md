# Gitless ResourceSet Image Automation

## Purpose

Flux Operator `ResourceSetInputProvider` resources now select permitted OCI image tags and digests in-cluster. The selected image is written to a workload-local ConfigMap named `<workload>-image-auto`; the existing HelmRelease or Flux Kustomization consumes that ConfigMap. Normal image changes therefore do **not** create a Git commit or pull request.

Git remains the source of truth for image policy, charts, storage, networking, credentials, and rollback pins. ResourceSets own only the generated ConfigMaps, never the existing HelmRelease objects. This prevents a ResourceSet and the root `apps` Kustomization (which has pruning enabled) from competing for ownership of a workload.

## Scope

The Gitless adapter is active for these workloads:

- `arkham`: bazarr, configarr, flaresolverr, jellyfin, lidarr, msmtpd, pihole, plex, prowlarr, qbittorrent, radarr, sonarr, unmonitorr.
- `ai`: openclaw.
- `error-pages`: error-pages.
- `n8n`: n8n.
- `registry`: registry.
- `monitoring`: grafana-mcp.

RaiPlaySoundRSS has a staged provider manifest but is not active: its `apps/kyrion/raiplaysoundrss` overlay is not included by the `apps` root Kustomization, so no namespace, ResourceSet, ConfigMap consumer, or legacy-policy cleanup has been rolled out for it.

The active workloads that remain on Flux ImagePolicy/ImageUpdateAutomation are apprise-api, overseerr, and tautulli. Their current `filterTags.extract` semantics cannot be represented safely by Flux Operator `OCIArtifactTag` in version `v0.57.0`: tags such as `version-v1.10.0` cannot use the provider SemVer selector without losing numeric ordering. Do not convert them to lexical selection merely to remove the final Git writes.

SearXNG also has an extraction-based legacy manifest, but its base is not selected by the `ai` overlay, so it has no live ImagePolicy or workload in this rollout. `RomM` is not included because it has no ImagePolicy setter target.

## How it works

Each migrated workload has `resourceset-image-automation.yaml` next to its current manifest:

1. `ResourceSetInputProvider/<workload>-image` scans the OCI image repository at `fluxcd.controlplane.io/reconcileEvery`.
2. Its `filter` admits one tag (`limit: 1`) and exports the tag plus its immutable SHA256 digest.
3. `ResourceSet/<workload>-image` generates `ConfigMap/<workload>-image-auto` with repository/tag/digest keys; Helm adapters also include a `values.yaml` key.
4. The ConfigMap label `reconcile.fluxcd.io/watch: Enabled` triggers the consuming HelmRelease or Kustomization to reconcile promptly.

For Helm workloads, the generated `values.yaml` is appended to `spec.valuesFrom`; the local `onechart` preserves the `repository:tag@digest` image form. n8n and OpenClaw use `postBuild.substituteFrom` with only valid substitution-variable keys; OpenClaw updates both its gateway and init-container image from the same digest-pinned value.

## Normal operations

Inspect a workload without reading any Secret values:

```bash
kubectl -n <namespace> get resourceset,resourcesetinputprovider
kubectl -n <namespace> get configmap <workload>-image-auto
flux get helmreleases -A
flux get kustomizations -A
```

A healthy image update has this ordering:

1. the input provider is Ready and exports the selected tag/digest;
2. the ResourceSet is Ready and refreshes its ConfigMap;
3. the HelmRelease or Kustomization is Ready;
4. the Deployment is available, or ConfigArr's scheduled Job completes successfully;
5. ResourceSet/provider and workload alerts remain clear for a full normal provider interval.

## Freeze an automatic update

Use the following only for incident response. Persist the chosen freeze immediately in Git after the emergency action.

```bash
kubectl -n <namespace> annotate resourceset <workload>-image \
  fluxcd.controlplane.io/reconcile=disabled --overwrite
kubectl -n <namespace> annotate resourcesetinputprovider <workload>-image \
  fluxcd.controlplane.io/reconcile=disabled --overwrite
```

The generated ConfigMap and deployed workload remain at their last applied image. Re-enable only after deciding whether to resume automation or pin a known-good image:

```bash
kubectl -n <namespace> annotate resourceset <workload>-image \
  fluxcd.controlplane.io/reconcile=enabled --overwrite
kubectl -n <namespace> annotate resourcesetinputprovider <workload>-image \
  fluxcd.controlplane.io/reconcile=enabled --overwrite
```

To freeze every Gitless target, annotate every ResourceSet and InputProvider selected by `app.kubernetes.io/component=image-automation`; then commit the matching annotation changes to Git. Do not re-enable `ImageUpdateAutomation/image-update` for a migrated workload: that would create a second writer.

## Roll back one workload

ResourceSet history and Helm release history are evidence, not an automatic functional rollback. A Pod may be Ready while the service is still broken. Alerting, application probes, and operator judgement decide the rollback.

1. Freeze the workload ResourceSet and provider.
2. Record the known-good `repository`, `tag`, and `digest` from the prior ConfigMap, ResourceSet history, HelmRelease history, or incident record. Use the digest as well as the tag.
3. In the workload's `resourceset-image-automation.yaml`, replace `spec.inputsFrom` with a single static `spec.inputs` item:

   ```yaml
   spec:
     inputs:
       - repository: example.registry/project/image
         tag: "known-good-tag"
         digest: "sha256:known-good-digest"
     wait: true
     resourcesTemplate: |
       # retain the existing ConfigMap template unchanged
   ```

   Remove `inputsFrom` entirely: inline `inputs` and dynamic `inputsFrom` are concatenated by default and are not a fallback relationship.
4. Commit the pin, reconcile through Git, then verify the ConfigMap, HelmRelease/Kustomization, workload availability, and application health.
5. Keep the pin until root cause is resolved. A separate reviewed change can restore `inputsFrom` and resume automatic selection.

For stateful workloads or images that run database migrations, do not rely on automatic Helm rollback. Pin the known-good digest and follow the workload-specific recovery procedure before attempting a downgrade.

## Alerting and validation

`monitoring/configs/resourceset-image-automation-rules.yaml` alerts when a ResourceSet or provider is non-ready, a migrated Deployment is unavailable, or a ConfigArr Job fails. `kube-state-metrics` is configured to export ResourceSet and provider readiness/revision metrics.

Before migrating a policy or changing its filter:

```bash
kustomize build apps/kyrion/<namespace>
flux build kustomization apps --path clusters/kyrion
kubectl apply --server-side --dry-run=server -f apps/base/<workload>/resourceset-image-automation.yaml
```

Validate the provider's selected tag and, where the legacy policy reflects one, digest against the prior ImagePolicy selection before removing a legacy policy. For tag formats that require extraction or non-standard ordering, retain the legacy ImagePolicy until equivalent behavior has been demonstrated.

## Recovery to Flux Image Automation

Use this only if the ResourceSet adapter itself is faulty:

1. Freeze the ResourceSet/provider.
2. Restore the workload's legacy ImageRepository, ImagePolicy, marker, and static image value from Git history, pinned first to the known-good image.
3. Remove the ConfigMap reference from the HelmRelease or Kustomization so the ResourceSet cannot update the workload.
4. Re-enable ImageUpdateAutomation only after it is the only image writer for that workload.
5. Do not delete ResourceSet CRDs, the Flux namespace, or registry Secrets as part of recovery.

## Related documentation

- [Flux Operator migration](flux-operator-migration.md)
- [HelmRelease recovery](helm-release-recovery.md)
- [Flux Operator ResourceSet image automation](https://fluxoperator.dev/docs/resourcesets/image-automation/)
