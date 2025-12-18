---
agent: 'agent'
model: Claude Sonnet 4
tools: ['search']
description: 'Deploy a new application to the Kubernetes cluster using Flux GitOps'
---

# Deploy New Application

You are helping deploy a new application to the Elysium Kubernetes homelab using Flux CD GitOps patterns.

## Required Information

Ask the user for the following if not provided:
1. **Application name** (kebab-case)
2. **Deployment method**: HelmRelease, Kustomize, or raw manifests
3. **Namespace** (create new or use existing)
4. **Helm chart source** (if using Helm): Follow the [chart selection priority](../copilot-instructions.md#helm--kustomize-integration) (official charts → community charts → Kustomize → onechart as last resort)
5. **Required secrets**: authentication tokens, API keys, etc.
6. **Ingress requirements**: Internal (Tailscale) or external
7. **Storage needs**: PersistentVolumeClaim requirements
8. **Dependencies**: Other apps or infrastructure components

## Chart Selection Guidelines

**See detailed chart selection priority in [Copilot Instructions](../copilot-instructions.md#helm--kustomize-integration).**

## Implementation Workflow

**Follow the detailed step-by-step procedure**: [docs/runbooks/add-application.md](/docs/runbooks/add-application.md)

The runbook covers:
- Creating base directory structure (Helm vs Kustomize)
- Registering in base kustomization
- Creating environment overlays with patches
- Creating sealed secrets
- Validation procedures (mandatory before commit)
- Helm rendering tests
- Commit with conventional commit message
- Deployment monitoring
- Troubleshooting common issues

**Key principles to follow**:
1. **Base directory** (`apps/base/<app>/`):
   - One resource per YAML file
   - Only environment-agnostic values
   - NO patches (patches belong in overlays)
   - Namespace only for app-specific namespaces (not `default`, `flux-system`, `kube-system`)
   
2. **Overlay directory** (`apps/kyrion/`):
   - Strategic merge patches for structural changes
   - JSON patches for precise value changes
   - Environment-specific ConfigMaps and SealedSecrets
   - Reference base directory, don't duplicate resources

3. **Version management**:
   - Pin all chart versions: `version: "1.2.3"`
   - Pin all image tags: `tag: "v1.2.3"`
   - Never use `latest` tags

4. **Validation (mandatory before commit)**:
   ```bash
   kustomize build apps/base/<app>/
   kustomize build apps/kyrion/
   flux build kustomization apps --path clusters/kyrion
   helm template <app> <chart> -f values.yaml  # if HelmRelease
   ```

## Validation Steps

After deployment:
1. Check HelmRelease status: `kubectl get hr -n <app-name>`
2. Verify pods are running: `kubectl get pods -n <app-name>`
3. Check logs: `kubectl logs -n <app-name> -l app=<app-name>`
4. Test ingress access (if configured)
5. Verify secrets mounted correctly

## Quick Reference Templates

For complete templates and examples, see [docs/runbooks/add-application.md](/docs/runbooks/add-application.md).

### Base HelmRelease Template
```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: <app>
  namespace: <namespace>
spec:
  interval: 1h
  timeout: 10m
  chart:
    spec:
      chart: <chart-name>
      version: "1.2.3"  # Pinned version
      sourceRef:
        kind: HelmRepository
        name: <repo-name>
        namespace: flux-system
  values:
    # Conservative defaults
    replicaCount: 1
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
  valuesFrom:  # Optional environment-specific values
    - kind: ConfigMap
      name: <app>-config
      optional: true
```

### Sealed Secret Creation
```bash
kubectl create secret generic <app>-secret \
  --namespace=<namespace> \
  --from-literal=key=value \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > <app>-sealed-secret.yaml
```

## References

- **[Repository Structure Standards](/docs/standards/repository-structure.md)** - File placement rules and best practices
- **[Add Application Runbook](/docs/runbooks/add-application.md)** - Complete step-by-step procedure
- **[Kubernetes Guidelines](/.github/instructions/kubernetes.instructions.md)** - Manifest best practices
- **[Flux Patterns](/.github/instructions/flux.instructions.md)** - GitOps conventions
- **[Helm Instructions](/.github/instructions/helm.instructions.md)** - Chart management
- **[Kustomize Instructions](/.github/instructions/kustomize.instructions.md)** - Overlay patterns
