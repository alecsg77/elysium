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
4. **Helm chart source** (if using Helm): Follow the [chart selection priority](../.github/copilot-instructions.md#helm--kustomize-integration) (official charts → community charts → Kustomize → onechart as last resort)
5. **Required secrets**: authentication tokens, API keys, etc.
6. **Ingress requirements**: Internal (Tailscale) or external
7. **Storage needs**: PersistentVolumeClaim requirements
8. **Dependencies**: Other apps or infrastructure components

## Chart Selection Guidelines

**See detailed chart selection priority in [Copilot Instructions](../copilot-instructions.md#helm--kustomize-integration).**

When deploying with Helm, always prioritize official charts:

### Quick Priority Reference:
1. **Official Chart from App Owner** - Example: `coder` from https://helm.coder.com/v2
2. **Official Documentation Method** - Check the app's official docs for recommended chart
3. **Community/Vendor Charts** - Bitnami, Grafana, Prometheus community, etc.
4. **Official Kustomize** - If app provides Kustomize manifests (like n8n)
5. **onechart** - Only when no other options exist

### How to Find Official Charts:
1. Check the application's GitHub repository for a `charts/` or `helm/` directory
2. Look in the official documentation for "Helm installation" or "Kubernetes deployment"
3. Search for official Helm repositories (often `https://helm.<app-domain>.com` or similar)
4. Check ArtifactHub.io for charts with "official" or "verified publisher" badges

## Implementation Steps

### 1. Create Base Application Directory
Create `apps/base/<app-name>/` with:
- `kustomization.yaml` - List all resources and dependencies
- `namespace.yaml` - Namespace definition with labels
- `release.yaml` or individual service YAML files
- `ts-ingress.yaml` (if Tailscale access needed)

### 2. Create Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: <app-name>
  labels:
    app.kubernetes.io/name: <app-name>
    pod-security.kubernetes.io/enforce: restricted
```

### 3. Create HelmRelease (if applicable)
```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: <app-name>
  namespace: <app-name>
spec:
  interval: 30m
  chart:
    spec:
      chart: <chart-name>
      version: <version>
      sourceRef:
        kind: HelmRepository
        name: <repo-name>
        namespace: flux-system
  values:
    # Base values here
```

### 4. Handle Secrets
If secrets are required:
1. Ask user for secret values (will be encrypted)
2. Create sealed secret:
   ```bash
   echo -n "value" | kubectl create secret generic <app>-secret \
     --dry-run=client --from-file=key=/dev/stdin -o yaml | \
     kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml
   ```
3. Save as `apps/base/<app>/<app>-sealed-secret.yaml`
4. Reference in HelmRelease via `valuesFrom`

### 5. Create Kustomization
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml
  - release.yaml
  # Add other resources
```

### 6. Add to Environment Overlay
Update `apps/kyrion/kustomization.yaml`:
```yaml
resources:
  - ../base/<app-name>
```

Add environment-specific patches if needed in `apps/kyrion/<app>-patch.yaml`

### 7. Commit and Deploy
Commit changes to Git. Flux will automatically detect and deploy within 5 minutes, or trigger immediately:
```bash
flux reconcile source git flux-system
flux reconcile kustomization apps
```

## Validation Steps

After deployment:
1. Check HelmRelease status: `kubectl get hr -n <app-name>`
2. Verify pods are running: `kubectl get pods -n <app-name>`
3. Check logs: `kubectl logs -n <app-name> -l app=<app-name>`
4. Test ingress access (if configured)
5. Verify secrets mounted correctly

## Common Patterns

### Tailscale Ingress for Private Access
```yaml
apiVersion: tailscale.com/v1alpha1
kind: ProxyClass
metadata:
  name: <app>-ingress
spec:
  statefulSet:
    labels:
      app: <app>
```

### Storage with Existing PVC
```yaml
persistence:
  enabled: true
  existingClaim: pvc-storage
  subPath: <app-data>
```

### Resource Limits
```yaml
resources:
  limits:
    cpu: 1000m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

Ensure the application follows the [Kubernetes guidelines](../.github/instructions/kubernetes.instructions.md) and [Flux patterns](../.github/instructions/flux.instructions.md).
