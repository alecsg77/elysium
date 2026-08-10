# Migrating Flux to Flux Operator

## Overview

This runbook migrates the existing Flux CLI bootstrap to a `FluxInstance` managed by Flux Operator without intentionally interrupting reconciliation. It follows the [Flux Operator migration guide](https://fluxoperator.dev/docs/guides/migration/).

The migration is deliberately split into independently verifiable GitOps changes:

1. Install Flux Operator and its CRDs.
2. Create an equivalent `FluxInstance` named `flux` and verify resource adoption.
3. Remove the legacy generated bootstrap manifests only after the instance is stable.
4. Install `flux-operator-mcp` as an internal, read-only service.

**This repository now implements phases 1 through 4.** The generated bootstrap manifests were removed only after the operator-managed instance, adopted root sync, six Flux controllers, image automation, and all root Kustomizations were verified healthy. Phase 4 is reconciled as an internal-only, read-only service with a dedicated Kubernetes identity; complete its post-reconciliation checks before relying on it operationally.

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

They render `FluxInstance/flux` in `flux-system`; the Flux Operator API only accepts that name and requires the instance in the same namespace as the operator. The HelmRelease depends on `flux-operator`, but does not gate readiness through the chart healthcheck: it is disabled because the chart's healthcheck Job cannot render digest-suffixed chart versions as valid Kubernetes labels. Validate `FluxInstance` readiness at runtime instead.

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

> **Image automation branch configuration:** a bootstrap `GitRepository` commonly uses `.spec.ref.branch`, while the `GitRepository` generated by `FluxInstance` represents the same branch as `.spec.ref.name` (for example, `refs/heads/main`). `ImageUpdateAutomation` cannot infer its push target from that name reference. Before or with adoption, configure both `.spec.git.checkout.ref.branch: main` and `.spec.git.push.branch: main` explicitly, while preserving its existing `sourceRef`, author, commit template, update strategy, and path.

Validate `FluxInstance` readiness and its control of the root sync with the operator and Flux CLIs:

```bash
flux reconcile helmrelease flux-instance -n flux-system --with-source
flux get helmrelease flux-instance -n flux-system
kubectl -n flux-system wait --for=condition=Ready fluxinstance/flux --timeout=10m
kubectl -n flux-system get fluxinstance flux
flux trace kustomization flux-system
flux get all -A
```

The expected trace is that `Kustomization/flux-system` is no longer managed by the legacy Flux bootstrap and is managed through the `FluxInstance`. Check the Ready status of `infra-controllers`, `infra-configs`, `apps`, `monitoring-controllers`, and `monitoring-configs` before proceeding.

## Phase 3: controlled bootstrap cleanup

After an entire successful reconciliation cycle with the instance in control, remove the legacy generated bootstrap manifests in a dedicated commit:

- `clusters/kyrion/flux-system/gotk-components.yaml`
- `clusters/kyrion/flux-system/gotk-sync.yaml`

The cleanup also deletes `clusters/kyrion/flux-system/kustomization.yaml`: Kustomize does not accept an empty overlay. Do not combine this deletion with the operator or instance installation. Before and after the cutover, confirm the instance still syncs `./clusters/kyrion`, no controller is duplicated, and all root Kustomizations are Ready.

### Rollback

- **Before bootstrap cleanup:** revert or suspend the instance HelmRelease and retain the legacy bootstrap. Do not remove the Secret or CRDs.
- **After bootstrap cleanup:** restore the pre-migration bootstrap manifests from the recorded commit first, validate source and root-sync readiness, then suspend or remove the instance in a separate change.
- **Operator-only rollback:** revert the phase-1 manifests. Do not manually delete CRDs or the `flux-system` namespace.

## Phase 3.5: Gitless workload image automation

After the operator-managed control plane is stable, workload image updates can move from Git-writing Flux Image Automation to Flux Operator ResourceSets. The implementation uses a ResourceSet-generated ConfigMap consumed by the existing HelmRelease or Flux Kustomization, so the workload object remains owned by the Git root and no image-update commit is needed for normal tag/digest changes.

See [Gitless ResourceSet Image Automation](resourceset-image-automation.md) for the supported workloads, tag-format exclusions, alerting, freeze, and digest-pinned rollback procedure. Do not remove the remaining `ImageUpdateAutomation/image-update` until every legacy marker has a semantically equivalent ResourceSet provider.

## Phase 4: Flux Operator MCP

The repository deploys the official `flux-operator-mcp` OCI Helm chart at version `0.57.0`, pinned to its OCI digest, through these manifests:

- `infrastructure/controllers/flux-operator-mcp/repository.yaml`
- `infrastructure/controllers/flux-operator-mcp/serviceaccount.yaml`
- `infrastructure/controllers/flux-operator-mcp/clusterrole.yaml`
- `infrastructure/controllers/flux-operator-mcp/clusterrolebinding.yaml`
- `infrastructure/controllers/flux-operator-mcp/release.yaml`

The HelmRelease waits for the `flux-operator` HelmRelease, enables Streamable HTTP at `/mcp`, and is explicitly configured as read-only. It remains a separate service from the local stdio MCP configurations in `.mux/mcp.jsonc` and `.vscode/mcp.json`; those clients continue to use their local binary unless deliberately reconfigured to reach a trusted port-forward or proxy.

### Access and identity boundary

The Service is a `ClusterIP` Service in `flux-system`, listening on port `9090`. Ingress and Gateway API HTTPRoute are disabled. The chart NetworkPolicy permits connections only from the `flux-system` namespace; use `kubectl port-forward` from a trusted administrative environment for the initial smoke test:

```bash
kubectl port-forward -n flux-system svc/flux-operator-mcp 9090:9090
```

Connect an HTTP-capable MCP client to `http://localhost:9090/mcp` only through that trusted tunnel. Do not expose this endpoint publicly without a separately reviewed TLS, authentication, and NetworkPolicy design.

Flux Operator MCP does not implement incoming OIDC authentication, bearer-token validation, token exchange, or per-request Kubernetes impersonation. It acts as its configured backend Kubernetes identity. The deployment therefore uses the dedicated `flux-operator-mcp-readonly` ServiceAccount, not the chart's default `cluster-admin` binding. Its ClusterRole permits only the read operations needed for Flux Operator/Flux Toolkit status, events, pod logs, and pod metrics; it intentionally does not grant any Secret access, mutation verbs, or wildcard resource access. Helm release inventory is unavailable because that optional feature requires reading Helm storage Secrets.

### Post-reconciliation validation

From a trusted administrative environment, verify the source, release, workload, and permission boundary:

```bash
flux get sources oci -n flux-system
flux get helmreleases -n flux-system
kubectl -n flux-system get deployment,service,networkpolicy flux-operator-mcp
kubectl auth can-i --as=system:serviceaccount:flux-system:flux-operator-mcp-readonly list helmreleases.helm.toolkit.fluxcd.io --all-namespaces
kubectl auth can-i --as=system:serviceaccount:flux-system:flux-operator-mcp-readonly get pods/log --all-namespaces
kubectl auth can-i --as=system:serviceaccount:flux-system:flux-operator-mcp-readonly get secrets --all-namespaces
kubectl auth can-i --as=system:serviceaccount:flux-system:flux-operator-mcp-readonly create helmreleases.helm.toolkit.fluxcd.io --all-namespaces
```

The first two authorization checks must return `yes`; the Secret and mutation checks must return `no`. Through the port-forward, verify the `/mcp` HTTP endpoint can retrieve Flux status and that mutation tools such as reconcile, suspend, resume, apply, and delete are absent or rejected in read-only mode.

Do not add an OIDC token through `--kube-token` to this workload: it would configure a static outbound Kubernetes credential, not authenticate MCP callers. Per-user Kubernetes RBAC requires a separately designed OIDC-aware adapter or controlled impersonation layer.

## Repository validation

Run these before every migration-phase commit:

```bash
kustomize build infrastructure/controllers
kustomize build infrastructure/configs
kubectl apply --dry-run=server -k infrastructure/controllers/flux-operator-mcp
yamllint .
```

Also run a local Flux dry-run build for the changed layer and the equivalent `infra-configs` build after any existing cluster-Kustomization patch mismatches have been resolved:

```bash
flux build kustomization infra-controllers \
  --path ./infrastructure/controllers \
  --kustomization-file clusters/kyrion/infrastructure.yaml \
  --dry-run
```

These builds validate the rendered Flux path while intentionally skipping values substituted from the cluster Secret.

For a chart change, also render the exact pinned chart and inspect CRDs, RBAC, NetworkPolicy, Service, and generated Flux resources before merging.

## Related documentation

- [Repository structure](../standards/repository-structure.md)
- [HelmRelease recovery](helm-release-recovery.md)
- [Flux Operator migration guide](https://fluxoperator.dev/docs/guides/migration/)
- [Flux Operator chart](https://github.com/controlplaneio-fluxcd/charts/tree/main/charts/flux-operator)
- [Flux Instance chart](https://github.com/controlplaneio-fluxcd/charts/tree/main/charts/flux-instance)
- [Flux Operator MCP chart](https://github.com/controlplaneio-fluxcd/charts/tree/main/charts/flux-operator-mcp)
