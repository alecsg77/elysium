# Migrating Flux to Flux Operator

## Overview

This runbook migrates the existing Flux CLI bootstrap to a `FluxInstance` managed by Flux Operator without intentionally interrupting reconciliation. It follows the [Flux Operator migration guide](https://fluxoperator.dev/docs/guides/migration/).

The migration is deliberately split into independently verifiable GitOps changes:

1. Install Flux Operator and its CRDs.
2. Create an equivalent `FluxInstance` named `flux` and verify resource adoption.
3. Remove the legacy generated bootstrap manifests only after the instance is stable.
4. Optionally install `flux-operator-mcp` as an internal, read-only service.

**This repository change implements phases 1 and 2.** The existing bootstrap manifests remain in Git as the fallback until the phase-2 runtime checks succeed; phase 3 bootstrap cleanup is a separate change.

## Safety requirements

- Reconcile changes through Git and Flux; do not use direct `kubectl apply` to perform the migration.
- Do not rotate, export, or commit the bootstrap Secret named `flux-system`.
- Do not remove `clusters/kyrion/flux-system/gotk-components.yaml` or `gotk-sync.yaml` in the operator-install change.
- Use a separate reviewed commit for every migration phase and retain the pre-migration commit SHA for rollback.
- Do not uninstall Flux Operator CRDs as part of a routine rollback. The chart marks its CRDs with Helm's keep policy.

## Prerequisites

- Administrative cluster access through a trusted environment, plus `kubectl`, `flux`, and `helm`.
- Kubernetes server version compatible with the selected chart release. The chart README for `flux-operator` `0.57.0` requires Kubernetes 1.30+ and Helm 3.8+.
- All current Flux controllers, sources, and Kustomizations are Ready.
- Pull access to `ghcr.io/controlplaneio-fluxcd`.

Capture a redacted baseline before changing Git:

```bash
kubectl version --output=yaml
helm version
flux version
flux get all -A
kubectl -n flux-system get deployment,gitrepository,kustomization,helmrelease
kubectl -n flux-system get secret flux-system -o name
```

Do not use `-o yaml` for the Secret. Record the names, revisions, and Ready conditions outside the repository if an operational snapshot is required.

## Phase 1: install Flux Operator

The GitOps manifests are located at:

- `infrastructure/controllers/flux-operator/repository.yaml`
- `infrastructure/controllers/flux-operator/release.yaml`
- `infrastructure/controllers/flux-operator/kustomization.yaml`

They install the official OCI chart in `flux-system`, pin chart tag `0.57.0` and its verified OCI digest, install CRDs, and leave the optional web UI disabled. The chart's cluster-wide RBAC remains enabled because Flux Operator needs it to manage a cluster-level Flux control plane.

### Validate phase 1

After Flux applies the commit, wait for the source and release, then confirm the CRD and Deployment:

```bash
flux reconcile kustomization infra-controllers --with-source
flux reconcile source oci flux-operator -n flux-system
flux reconcile helmrelease flux-operator -n flux-system --with-source

kubectl -n flux-system get ocirepository,helmrelease,deploy flux-operator
kubectl get crd fluxinstances.fluxcd.controlplane.io
kubectl -n flux-system get deploy \
  source-controller,kustomize-controller,helm-controller,notification-controller,\
  image-reflector-controller,image-automation-controller
flux get all -A
```

**Exit condition:** `OCIRepository/flux-operator` and `HelmRelease/flux-operator` are Ready, `FluxInstance` CRDs exist, and the six pre-existing Flux controller Deployments remain Ready. If any condition fails, revert the phase-1 Git commit and investigate without touching the legacy bootstrap.

## Phase 2: create an equivalent FluxInstance

Only start this phase after phase 1 has been stable for at least one normal reconciliation interval.

The phase-2 GitOps manifests use the pinned `flux-instance` chart and are located at:

- `infrastructure/configs/flux-instance/repository.yaml`
- `infrastructure/configs/flux-instance/release.yaml`
- `infrastructure/configs/flux-instance/kustomization.yaml`

They render `FluxInstance/flux` in `flux-system`; the Flux Operator API only accepts that name and requires the instance in the same namespace as the operator. The HelmRelease depends on `flux-operator` and waits on the chart health check for the instance to become Ready.

Before rendering the instance, copy the live bootstrap configuration exactly:

```bash
kubectl -n flux-system get gitrepository flux-system \
  -o jsonpath='{.spec.url}{"\n"}{.spec.ref.branch}{"\n"}{.spec.secretRef.name}{"\n"}'
kubectl -n flux-system get kustomization flux-system \
  -o jsonpath='{.spec.path}{"\n"}{.spec.interval}{"\n"}{.spec.prune}{"\n"}'
```

The phase-2 release pins both the `flux-instance` chart and the matching Flux distribution artifact. The artifact must contain the exact adopted Flux version; validate this before changing the pin.

The instance values must preserve:

- Flux distribution version `2.9.3` (held exactly during adoption), registry/artifact, and all six current controllers.
- Cluster domain, network policy, tenancy, storage, common metadata, and any generated-manifest patches.
- Git sync kind, URL, branch/ref, path, interval, prune behavior, and pull Secret.
- Existing image automation resources; do not remove or rename `ImageUpdateAutomation/image-update` during adoption.

After the `FluxInstance` is Ready, validate its control of the root sync:

```bash
kubectl -n flux-system get fluxinstance flux
flux trace kustomization flux-system
flux get all -A
```

The expected trace is that `Kustomization/flux-system` is no longer managed by the legacy Flux bootstrap and is managed through the `FluxInstance`. Check the Ready status of `infra-controllers`, `infra-configs`, `apps`, `monitoring-controllers`, and `monitoring-configs` before proceeding.

## Phase 3: controlled bootstrap cleanup

Only after an entire successful reconciliation cycle with the instance in control, remove the legacy generated bootstrap manifests in a dedicated commit:

- `clusters/kyrion/flux-system/gotk-components.yaml`
- `clusters/kyrion/flux-system/gotk-sync.yaml`

Do not combine this deletion with the operator or instance installation. Confirm again that the instance still syncs `./clusters/kyrion`, no controller is duplicated, and all root Kustomizations are Ready.

### Rollback

- **Before bootstrap cleanup:** revert or suspend the instance HelmRelease and retain the legacy bootstrap. Do not remove the Secret or CRDs.
- **After bootstrap cleanup:** restore the pre-migration bootstrap manifests from the recorded commit first, validate source and root-sync readiness, then suspend or remove the instance in a separate change.
- **Operator-only rollback:** revert the phase-1 manifests. Do not manually delete CRDs or the `flux-system` namespace.

## Phase 4: optional Flux Operator MCP

Deploy MCP only after the Flux migration is stable and after approving its client namespace and RBAC model. It is a separate service from the local stdio MCP configuration in `.mux/mcp.jsonc` and `.vscode/mcp.json`.

The production baseline must be:

```yaml
transport: http
readonly: true
ingress:
  enabled: false
httpRoute:
  enabled: false
networkPolicy:
  create: true
```

Keep the Service internal. Initially use `kubectl port-forward` for trusted administrative testing rather than exposing it with an Ingress or HTTPRoute. The chart's default ServiceAccount binding is `cluster-admin`; disable that generated binding if the chosen chart release permits it and provide a reviewed, least-privilege read-only RBAC policy. Block production rollout if that substitution cannot be validated.

Validate the `/mcp` HTTP endpoint, secret masking, NetworkPolicy denial from unauthorized namespaces, and that mutation tools such as reconcile, suspend, resume, apply, and delete are unavailable in read-only mode.

## Repository validation

Run these before every migration-phase commit:

```bash
kustomize build infrastructure/controllers
kustomize build infrastructure/configs
kubectl apply --dry-run=server -k infrastructure/controllers/flux-operator
yamllint .
```

Also run `flux build kustomization infra-controllers --path clusters/kyrion` and the equivalent `infra-configs` build after any existing cluster-Kustomization patch mismatches have been resolved. These full builds validate the rendered Flux path, but a pre-existing patch mismatch must not be attributed to the migration manifests.

For a chart change, also render the exact pinned chart and inspect CRDs, RBAC, NetworkPolicy, Service, and generated Flux resources before merging.

## Related documentation

- [Repository structure](../standards/repository-structure.md)
- [HelmRelease recovery](helm-release-recovery.md)
- [Flux Operator migration guide](https://fluxoperator.dev/docs/guides/migration/)
- [Flux Operator chart](https://github.com/controlplaneio-fluxcd/charts/tree/main/charts/flux-operator)
- [Flux Instance chart](https://github.com/controlplaneio-fluxcd/charts/tree/main/charts/flux-instance)
- [Flux Operator MCP chart](https://github.com/controlplaneio-fluxcd/charts/tree/main/charts/flux-operator-mcp)
