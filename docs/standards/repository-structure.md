# Repository Structure (Monorepo Standards)

This document defines the **authoritative repository structure** and the operating rules for maintaining a **clean, scalable Flux GitOps monorepo**.

If you are unsure where to add or update something, start here.

## Goals

- **Single source of truth**: all cluster state is defined in Git and reconciled by Flux.
- **Clear ownership**: every file has an obvious “home” and reason to exist.
- **Separation of concerns**: infrastructure, monitoring, and apps evolve independently.
- **Environment overlays**: base manifests are reusable; environment overlays are minimal deltas.
- **Safe-by-default**: secrets are always encrypted; changes are reviewed and reproducible.

## Repository structure (contract)

This repository follows a layered GitOps layout inspired by common Flux patterns (including the flux2 kustomize+helm example), adapted for this cluster.

### Top-level directories

| Path | Purpose | Rules |
|------|---------|-------|
| `clusters/` | **Cluster entry point(s)**. Flux `Kustomization` resources that define *what gets applied* and in which order. | Keep minimal. Only orchestration + cluster-wide vars/secrets. |
| `infrastructure/` | Controllers/operators and cluster-wide configuration (ingress, cert-manager, device plugins, policies, issuers, etc.). | Split `controllers/` (CRDs/operators) vs `configs/` (their configuration). |
| `apps/` | User/workload applications. Typically `HelmRelease` + supporting manifests. | Use `base/` + environment overlays (e.g. `kyrion/`). |
| `monitoring/` | Observability stack (controllers + configs), often independent from apps. | Keep dashboards, datasources, monitors here; avoid scattering. |
| `docs/` | Human documentation: architecture, standards, runbooks, troubleshooting. | Prefer linking to source manifests instead of copying YAML. |
| `functions/` | Fission specs / serverless functions and deployment artifacts. | Treat as its own “domain”; keep specs versioned. |
| `coder/` | Coder templates and related developer-experience assets. | Keep templates self-contained. |
| `etc/` | Local/operator artifacts like kubeconfig and certs. | Never commit private keys or plaintext credentials. |
| `scripts/` | Bootstrap and automation scripts. | Scripts must be idempotent when possible. |

### Layering and dependency ordering

The repository must preserve a strict dependency chain so that CRDs and infrastructure exist before workloads that need them:

1. `infrastructure/controllers` (operators, CRDs)
2. `infrastructure/configs` (cluster-wide config that depends on controllers)
3. `apps/*` (workloads)
4. `monitoring/*` (may be independent, but must still install controllers before configs)

Where this is expressed:

- Flux orchestration lives in `clusters/<cluster>/`.
- Kustomizations use `spec.dependsOn` to express ordering.
- HelmReleases use `spec.dependsOn` for intra-namespace ordering when needed.

## Monorepo hygiene rules

## Where should this file go? (decision tree)

Use this quick guide when adding or changing manifests.

1. **Is this a Flux orchestration object that defines ordering or paths?**
  - Yes → `clusters/<cluster>/` (e.g., Kustomizations that point at `apps/`, `infrastructure/`, `monitoring/`).
  - No → continue.

2. **Is it a controller/operator/CRD install (things that enable other resources)?**
  - Yes → `infrastructure/controllers/` (or `monitoring/controllers/` for observability operators).
  - No → continue.

3. **Is it configuration/policy for cluster-wide infrastructure?**
  Examples: issuers, ingress config, StorageClass, cluster DNS, shared HelmRepository sources.
  - Yes → `infrastructure/configs/`.
  - No → continue.

4. **Is it an application workload (HelmRelease, Deployment, Service, Ingress, app ConfigMap/Secret)?**
  - Yes → `apps/base/<app>/`.
    - If it is cluster-specific (hostnames, node selectors, storage classes, env-only settings) → put the delta in `apps/<env>/` as a patch.
  - No → continue.

5. **Is it observability configuration (dashboards, datasources, PodMonitors/ServiceMonitors, OTEL pipelines)?**
  - Yes → `monitoring/configs/` (or alongside the relevant monitoring component under `monitoring/controllers/<component>/` if tightly coupled).
  - No → continue.

6. **Is it a Secret?**
  - Cluster-wide variables used via Flux substitution → `clusters/<cluster>/sealed-secrets.yaml` (encrypted only).
  - App-specific credentials/config → `apps/base/<app>/*-sealed-secret.yaml` (encrypted only).
  - Never commit plaintext secrets anywhere.

7. **Is it documentation?**
  - General guides/runbooks/standards → `docs/`.
  - Component-specific operational notes → keep next to the component (e.g., `apps/base/<app>/README.md`, `monitoring/controllers/<component>/README.md`).

### 1) One resource, one home

- A resource should have exactly one authoritative definition in Git.
- Avoid duplicating the same `Namespace`, `HelmRepository`, or `ConfigMap` in multiple places.
- If multiple apps need a shared dependency (e.g., a cluster issuer), it belongs under `infrastructure/configs/`.

**Kustomize best practice**: Each YAML file should contain only one Kubernetes resource (exception: multi-document YAML with `---` is acceptable only when resources are tightly coupled and always deployed together, but prefer separate files for clarity and reusability).

### 2) Base vs overlay (Kustomize)

Use the base/overlay pattern everywhere it makes sense:

- `apps/base/<app>/` contains reusable manifests: `namespace.yaml`, `release.yaml`, service/ingress, dashboards, etc.
- `apps/<env>/` contains only environment-specific deltas: patches, env-only config, and env-only sealed secrets.

**Base directory rules (MUST follow):**

- ✅ **Environment-agnostic resources only**: No cluster-specific values (hostnames, node names, storage class names)
- ✅ **Complete, functional resources**: Base should work with sensible defaults
- ✅ **One resource per file**: Each YAML file contains exactly one Kubernetes resource
- ✅ **Logical grouping**: Related resources in same directory (app + service + ingress)
- ✅ **Conservative defaults**: Resource requests/limits should work on minimal hardware
- ❌ **No environment-specific values**: No `prod` hostnames, no `dev` replica counts
- ❌ **No patches in base**: Patches belong in overlays only

**Overlay directory rules (MUST follow):**

- ✅ **Patches only**: Use Kustomize patches to modify base resources
- ✅ **Environment-specific resources**: ConfigMaps, Secrets, resource limits specific to this environment
- ✅ **Small and focused**: Overlay should be minimal - only what differs from base
- ✅ **Strategic merge for structure**: Use when adding new sections (new env var, new volume)
- ✅ **JSON patch for precision**: Use for exact value changes (image tag, replica count, specific field)
- ❌ **No duplicated resources**: Don't copy entire manifests from base to overlay
- ❌ **No base-like content**: If many patches are needed, reconsider base design

**Patch file naming conventions:**

- `<resource-name>-patch.yaml` - Strategic merge patch
- `<resource-name>-json-patch.yaml` - JSON patch (JSON 6902)
- `<resource-name>-<purpose>-patch.yaml` - Specific purpose (e.g., `coder-resources-patch.yaml`)

**When to use each patch type:**

| Patch Type | Use Case | Example |
|------------|----------|----------|
| **Strategic Merge** | Add/modify entire sections | Add environment variable, add volume mount, modify entire container spec |
| **JSON Patch (6902)** | Precise single-value changes | Change image tag, set replica count, update one annotation |
| **Inline patch (patchesStrategicMerge)** | Simple field overrides | Small value changes inline in kustomization.yaml |

**Example: Good base structure**
```
apps/base/myapp/
├── kustomization.yaml       # Lists all resources, no patches
├── namespace.yaml           # (only for app-specific namespaces)
├── helmrelease.yaml         # HelmRelease with generic values
├── service.yaml             # Service definition
└── ingress.yaml             # Ingress template without specific host
```

**Example: Good overlay structure**
```
apps/kyrion/
├── kustomization.yaml       # References base, applies patches
├── myapp-host-patch.yaml    # Adds environment-specific hostname
├── myapp-resources-patch.yaml # Overrides resource limits
└── myapp-sealed-secret.yaml # Environment-specific secret
```

### 3) Naming conventions

Consistency matters more than creativity.

- **Namespaces**: match app name (e.g., `ai`, `coder`, `monitoring`), avoid suffixes unless necessary.
- **HelmRelease names**: match the app (e.g., `coder`, `loki`, `tempo`).
- **File naming**:
  - `namespace.yaml` for namespaces
  - `release.yaml` for HelmRelease (single chart)
  - `repository.yaml` for HelmRepository/OCIRepository definitions
  - `*-sealed-secret.yaml` for SealedSecret manifests
  - `*-values.yaml` or `*-values-patch.yaml` for values fragments/patches
- **Kustomizations**: in `clusters/<cluster>/`, choose names by layer (`infra-controllers`, `infra-configs`, `apps`, `monitoring-controllers`, `monitoring-configs`).

### 4) Secrets policy (non-negotiable)

- Never commit plaintext secrets.
- Use Bitnami Sealed Secrets (`SealedSecret`) and keep files named `*-sealed-secret.yaml`.
- Prefer referencing Secrets/ConfigMaps through:
  - Flux `spec.postBuild.substituteFrom` for *string substitution* in manifests.
  - HelmRelease `spec.valuesFrom` for Helm values injection.

If you need a new secret:

- Create it as a SealedSecret in the **same domain** as its consumer (app secret under `apps/base/<app>/`, cluster-wide secret under `clusters/<cluster>/sealed-secrets.yaml`).
- Add a minimal README note describing what the secret is for (never the secret value).

### 5) Helm chart management best practices

**Chart source selection (priority order):**

1. **Official chart from application owner** (e.g., `coder` from Coder.com)
2. **Official documentation recommendation** (what the app docs suggest)
3. **Verified publishers** (Bitnami, Prometheus Community, well-maintained vendors)
4. **Official Kustomize manifests** (use Flux Kustomization instead of HelmRelease)
5. **Generic wrappers (last resort)** (e.g., `onechart` for simple containers)

**Version management:**

- ✅ **Pin chart versions explicitly**: `spec.chart.spec.version: "1.2.3"`
- ✅ **Pin app image tags in values**: Avoid `latest` tag
- ✅ **Document version constraints**: Note why specific version is used
- ✅ **Use semantic version ranges sparingly**: Only when chart API is stable
- ❌ **Never use `latest` chart version**
- ❌ **Don't use `*` or floating versions in production**

**HelmRepository organization:**

- Define `HelmRepository`/`OCIRepository` resources in `infrastructure/configs/helm-repositories.yaml`
- Reuse repository references across all HelmReleases
- Group by vendor/source: bitnami, prometheus-community, official apps
- Use consistent naming: `<vendor>-charts` or `<app>-official`

**HelmRelease structure:**

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: myapp
  namespace: myapp
spec:
  interval: 1h
  chart:
    spec:
      chart: myapp
      version: 1.2.3              # Pinned version
      sourceRef:
        kind: HelmRepository
        name: myapp-official       # Centralized repository
        namespace: flux-system
  # Base values - environment-agnostic
  values:
    image:
      repository: myapp/myapp
      tag: v1.2.3                  # Pinned tag
    replicaCount: 1                # Conservative default
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
  # Reference to environment-specific values
  valuesFrom:
    - kind: ConfigMap
      name: myapp-config
      optional: true
    - kind: Secret
      name: myapp-secret
      optional: false
```

**Values management strategies:**

| Method | Use Case | Location |
|--------|----------|----------|
| **Inline values** | Base configuration, defaults | `spec.values` in base HelmRelease |
| **valuesFrom ConfigMap** | Environment-specific non-sensitive config | Overlay ConfigMap, referenced in base or overlay |
| **valuesFrom Secret** | Sensitive configuration | SealedSecret in overlay |
| **Kustomize patch** | Modify specific Helm values | Overlay patch file (JSON or strategic merge) |

**Anti-patterns to avoid:**

- ❌ **Duplicating entire values in overlay**: Use patches to modify specific paths
- ❌ **Mixing environment-specific values in base**: Keep base generic
- ❌ **Using `valuesFrom` for secrets without encryption**: Always use SealedSecret
- ❌ **Hardcoding credentials in values**: Use valuesFrom with Secret references
- ❌ **Not specifying `interval`**: Always set explicit reconciliation interval

### 6) Keep Flux reconciliation safe

- Use `prune: true` for Kustomizations unless there is a very strong reason not to.
- Use `wait: true` and realistic `timeout` values for Kustomizations and HelmReleases.
- Add `dependsOn` rather than relying on “it usually applies in time”.

### 7) Don’t leak environment specifics into base

Keep these out of base:

- Cluster domain names
- Ingress hostnames specific to a cluster
- Node affinity tied to a particular node pool name
- StorageClass names that only exist in one cluster

Put them in the overlay patch instead.

## Adding or changing an application

When adding a new application or modifying existing ones, follow the complete step-by-step procedure documented in:

**→ [Adding or Changing an Application Runbook](/docs/runbooks/add-application.md)**

The runbook provides:
- Prerequisites and setup
- Detailed steps for Helm-based and Kustomize-based apps
- Validation procedures (mandatory before commit)
- Commit guidelines following Conventional Commits
- Deployment monitoring procedures
- Troubleshooting common issues
- Pre-commit checklist

**Quick reference** - Required structure:

```
apps/base/<app>/              # Base resources (environment-agnostic)
├── kustomization.yaml        # Resource list, NO patches
├── namespace.yaml            # Only if new app-specific namespace
├── helmrelease.yaml          # Or individual resource files
└── <resource>.yaml

apps/<env>/                   # Environment overlay
├── kustomization.yaml        # References base + patches
├── <app>-patch.yaml          # Environment-specific patches
├── <app>-config.yaml         # Environment ConfigMap
└── <app>-sealed-secret.yaml  # Encrypted secrets
```

**Key principles:**
- Base contains only environment-agnostic resources with sensible defaults
- Overlays contain only patches and environment-specific resources
- One Kubernetes resource per YAML file
- No system namespace declarations (`default`, `flux-system`, `kube-system`)
- All versions pinned (charts, images - no `latest`)
- Validate locally before committing (mandatory)
## Kustomize anti-patterns (what NOT to do)

Common mistakes that violate Kustomize best practices:

### Anti-pattern 1: Copying entire resources to overlays

❌ **Bad** - Duplicating full resource in overlay:
```yaml
# apps/kyrion/myapp-deployment.yaml (full copy from base)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3  # Only this changed!
  template:
    # ... 50 lines of duplicated config
```

✅ **Good** - Use patch for specific change:
```yaml
# apps/kyrion/myapp-replicas-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
```

### Anti-pattern 2: Environment-specific values in base

❌ **Bad** - Base contains environment-specific values:
```yaml
# apps/base/myapp/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
spec:
  rules:
  - host: myapp.prod.example.com  # Production-specific!
```

✅ **Good** - Base is generic, overlay adds specifics:
```yaml
# apps/base/myapp/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
spec:
  rules:
  - host: myapp.local  # Placeholder or omitted

# apps/kyrion/myapp-ingress-patch.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
spec:
  rules:
  - host: myapp.kyrion.example.com
```

### Anti-pattern 3: Multiple resources in one file

❌ **Bad** - Multiple resources in single file:
```yaml
# apps/base/myapp/resources.yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
```

✅ **Good** - One resource per file:
```
apps/base/myapp/
├── service.yaml
├── deployment.yaml
└── ingress.yaml
```

### Anti-pattern 4: Patches in base directory

❌ **Bad** - Base contains patches:
```yaml
# apps/base/myapp/kustomization.yaml
resources:
- deployment.yaml
patchesStrategicMerge:  # Patches in base!
- replicas-patch.yaml
```

✅ **Good** - Patches only in overlays:
```yaml
# apps/base/myapp/kustomization.yaml
resources:
- deployment.yaml  # Only resources

# apps/kyrion/kustomization.yaml
resources:
- ../../base/myapp
patchesStrategicMerge:
- myapp-replicas-patch.yaml  # Patches in overlay
```

### Anti-pattern 5: Using `resources` instead of `bases`

❌ **Bad** - Incorrect overlay structure:
```yaml
# apps/kyrion/kustomization.yaml
resources:
- ../base/myapp/deployment.yaml  # Cherry-picking files
- ../base/myapp/service.yaml
```

✅ **Good** - Reference base directory:
```yaml
# apps/kyrion/kustomization.yaml
resources:
- ../../base/myapp  # Reference entire base
patchesStrategicMerge:
- myapp-patch.yaml
```

### Anti-pattern 6: Declaring system namespaces

❌ **Bad** - App declares system namespace:
```yaml
# apps/base/myapp/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: default  # or flux-system, kube-system
```

✅ **Good** - Apps target existing namespaces:
```yaml
# apps/base/myapp/helmrelease.yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: myapp
  namespace: default  # Reference only, don't create
```
## Documentation placement rules

This repo intentionally uses two doc “layers”:

- **General docs** go under `docs/` (architecture, standards, runbooks, troubleshooting).
- **Code-adjacent docs** live next to the source when they are tightly coupled to a specific component (for example, a complex chart’s values/operational notes).

Always prefer:

- Linking to source manifests instead of duplicating them.
- Keeping README files short and practical (what it is, how to operate it, how to upgrade/rollback).

## Change standards

- Commit messages must follow Conventional Commits.
- Changes must be declarative (no “manual cluster-only changes” as the steady state).
- Keep diffs minimal and scoped to the component you are changing.

## References inside this repository

- Flux cluster entry points: `clusters/kyrion/*.yaml`
- Apps overlays: `apps/kyrion/`
- Apps bases: `apps/base/`
- Infrastructure: `infrastructure/controllers/` and `infrastructure/configs/`
- Monitoring: `monitoring/controllers/` and `monitoring/configs/`

## External references

- Flux documentation: https://fluxcd.io/docs/
- Flux guides and best practices: https://fluxcd.io/docs/guides/
