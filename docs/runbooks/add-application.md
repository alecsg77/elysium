# Adding or Changing an Application

Step-by-step runbook for adding new applications to the cluster or modifying existing ones.

## Prerequisites

- Git repository cloned locally
- `kustomize` CLI installed (v4.5+)
- `flux` CLI installed (v2.0+)
- `helm` CLI installed (v3.0+) - if using HelmRelease
- `yamllint` installed (optional but recommended)
- `kubeseal` CLI installed - if creating sealed secrets
- Access to sealed-secrets public key: `etc/certs/pub-sealed-secrets.pem`

## Overview

This runbook covers the complete workflow for adding a new application using Flux CD, Kustomize base/overlay pattern, and Helm (when applicable).

**Estimated Time**: 30-60 minutes for a new application

## Step 1: Create Base Directory Structure

### For Helm-based Applications

```bash
# Navigate to apps base directory
cd apps/base/

# Create app directory
mkdir -p <app>
cd <app>
```

**Directory structure:**
```
apps/base/<app>/
├── kustomization.yaml       # Resource list (NO patches)
├── namespace.yaml           # Only if new app-specific namespace
├── helmrelease.yaml         # HelmRelease with base values
└── <resource>.yaml          # Additional K8s resources (Service, Ingress, etc.)
```

**Create `kustomization.yaml`:**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml           # If app-specific namespace
  - helmrelease.yaml
  # Add one line per resource file

# NO patches, patchesStrategicMerge, or patchesJson6902 in base
# NO environment-specific values
# NO commonLabels/commonAnnotations unless truly universal
```

**Create `helmrelease.yaml`:**
```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: <app>
  namespace: <namespace>
spec:
  interval: 1h
  timeout: 10m               # Adjust based on deployment time
  chart:
    spec:
      chart: <chart-name>
      version: "1.2.3"       # Pin specific version
      sourceRef:
        kind: HelmRepository
        name: <repo-name>
        namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
      remediateLastFailure: true
  values:
    # Environment-agnostic defaults only
    replicaCount: 1
    image:
      repository: <image>
      tag: "v1.2.3"          # Pin specific tag
    resources:
      requests:              # Conservative defaults
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 512Mi
  # Optional: Reference environment-specific values
  valuesFrom:
    - kind: ConfigMap
      name: <app>-config
      optional: true
    - kind: Secret
      name: <app>-secret
      optional: true
```

**Create `namespace.yaml` (if needed):**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: <app>
  labels:
    app: <app>
```

**⚠️ Important**: Do NOT create namespace.yaml for system namespaces (`default`, `kube-system`, `flux-system`).

### For Kustomize-based Applications

```bash
cd apps/base/
mkdir -p <app>
cd <app>
```

**Directory structure:**
```
apps/base/<app>/
├── kustomization.yaml       # Resource list
├── namespace.yaml           # Only if new app-specific namespace
├── deployment.yaml          # One resource per file
├── service.yaml
└── ingress.yaml
```

**Create individual resource files** (one Kubernetes resource per file).

## Step 2: Register in Base Kustomization

Edit `apps/base/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  # ... existing apps ...
  - <app>/                   # Add new app directory
```

## Step 3: Create Environment Overlay

```bash
cd apps/kyrion/  # Or your environment name
```

**Overlay structure:**
```
apps/kyrion/
├── kustomization.yaml
├── <app>-<purpose>-patch.yaml    # Patches for base resources
├── <app>-config.yaml             # Environment-specific ConfigMap
└── <app>-sealed-secret.yaml      # Environment-specific secrets
```

**Create/update `kustomization.yaml`:**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base/<app>         # Reference base directory
  - <app>-config.yaml        # Env-specific resources
  - <app>-sealed-secret.yaml

# Strategic merge patches (for adding/modifying sections)
patchesStrategicMerge:
  - <app>-resources-patch.yaml
  - <app>-ingress-patch.yaml

# JSON patches (for precise value changes)
patchesJson6902:
  - target:
      kind: HelmRelease
      name: <app>
    path: <app>-replicas-json-patch.yaml
```

**Example strategic merge patch** (`<app>-ingress-patch.yaml`):
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: <app>
spec:
  rules:
  - host: <app>.kyrion.example.com  # Environment-specific hostname
```

**Example JSON patch** (`<app>-replicas-json-patch.yaml`):
```yaml
- op: replace
  path: /spec/values/replicaCount
  value: 3
```

## Step 4: Create Sealed Secrets (if needed)

### For Application Secrets

```bash
# Create secret (example: API key)
kubectl create secret generic <app>-secret \
  --namespace=<namespace> \
  --from-literal=api-key=<value> \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > apps/kyrion/<app>-sealed-secret.yaml
```

### For ConfigMaps

```bash
# Create ConfigMap
cat > apps/kyrion/<app>-config.yaml <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: <app>-config
  namespace: <namespace>
data:
  ENVIRONMENT: kyrion
  LOG_LEVEL: info
EOF
```

## Step 5: Validate Locally (MANDATORY)

### 5.1 Validate YAML Syntax

```bash
yamllint apps/base/<app>/ apps/kyrion/<app>-*
```

**Expected**: No errors or warnings (or only acceptable warnings).

### 5.2 Build Base

```bash
kustomize build apps/base/<app>/
```

**Expected**: Valid Kubernetes YAML output with no errors.

### 5.3 Build Overlay

```bash
kustomize build apps/kyrion/ | grep -A 20 "kind: HelmRelease"
```

**Expected**: Patches applied correctly, environment-specific values present.

### 5.4 Validate Flux Resources

```bash
flux build kustomization apps --path clusters/kyrion
```

**Expected**: `✔ kustomization 'apps' is valid`

### 5.5 Check for Common Issues

```bash
kustomize build apps/kyrion/ | grep -E "(latest|default|example.com)"
```

**Expected**: No `latest` tags, no example.com hostnames (unless intentional).

## Step 6: Test Helm Rendering (HelmRelease only)

```bash
# Extract values from built manifest
kustomize build apps/kyrion/ | yq 'select(.kind == "HelmRelease") | select(.metadata.name == "<app>") | .spec.values' > /tmp/test-values.yaml

# Test Helm template rendering
helm template <app> <chart-repo>/<chart> -f /tmp/test-values.yaml
```

**Expected**: Valid Kubernetes manifests without errors.

## Step 7: Commit Changes

### 7.1 Stage Changes

```bash
git add apps/base/<app>/
git add apps/kyrion/<app>-*
git add apps/base/kustomization.yaml
git add apps/kyrion/kustomization.yaml  # if modified
```

### 7.2 Create Commit

```bash
git commit -m "feat(apps): add <app> with <key-feature>

- Add <app> HelmRelease with version X.Y.Z
- Configure <specific-setting>
- Add environment-specific patches for kyrion
- Includes sealed secrets for <credential-type>

Closes #<issue-number>"
```

### 7.3 Push to Repository

```bash
git push origin main
```

**⚠️ Important**: Ensure you have reviewed changes before pushing. Flux will automatically reconcile within 5 minutes.

## Step 8: Monitor Deployment

### 8.1 Watch Flux Reconciliation

```bash
# Watch all kustomizations
flux get kustomizations -A --watch

# Wait for 'apps' kustomization to reconcile
# Expected: Ready=True
```

### 8.2 Check HelmRelease Status

```bash
# Check specific HelmRelease
flux get helmrelease <app> -n <namespace>

# Expected: Ready=True, Status=Release reconciliation succeeded
```

### 8.3 Verify Pods

```bash
kubectl get pods -n <namespace>

# Expected: Pods in Running state (x/x Ready)
```

### 8.4 Check Application Logs

```bash
kubectl logs -n <namespace> -l app=<app> --tail=50 --follow
```

**Expected**: No error messages, application started successfully.

### 8.5 Test Application Endpoints

```bash
# For Ingress-exposed apps
curl https://<app>.<domain>

# Expected: HTTP 200 response
```

## Pre-Commit Checklist

Before committing, verify:

- [ ] Base directory contains only environment-agnostic resources
- [ ] One resource per YAML file
- [ ] No system namespace declarations (`default`, `flux-system`, `kube-system`)
- [ ] Chart and image versions pinned (no `latest`)
- [ ] Patches are in overlay, not base
- [ ] `kustomize build` succeeds for both base and overlay
- [ ] `flux build` succeeds
- [ ] Helm template renders correctly (if applicable)
- [ ] Resource requests are conservative
- [ ] Secrets are encrypted with SealedSecret
- [ ] No plaintext credentials in values
- [ ] Conventional commit message format
- [ ] Changes tested locally

## Troubleshooting

### Issue: Kustomize build fails

**Symptoms**: `kustomize build` command returns errors

**Solutions**:
1. Check YAML syntax with `yamllint`
2. Verify resource file paths in `kustomization.yaml`
3. Ensure no circular dependencies
4. Check for duplicate resource definitions

### Issue: Flux reconciliation fails

**Symptoms**: `flux get kustomizations` shows `Ready=False`

**Solutions**:
```bash
# Check detailed status
kubectl describe kustomization apps -n flux-system

# Check Flux controller logs
kubectl logs -n flux-system deploy/kustomize-controller --tail=100

# Force reconciliation
flux reconcile kustomization apps
```

### Issue: HelmRelease fails to install

**Symptoms**: `flux get hr <app>` shows `Ready=False`

**Solutions**:
```bash
# Check HelmRelease details
kubectl describe helmrelease <app> -n <namespace>

# Check Helm controller logs
kubectl logs -n flux-system deploy/helm-controller | grep <app>

# Verify chart exists
helm search repo <repo>/<chart>

# Force reconciliation
flux reconcile helmrelease <app> -n <namespace>
```

### Issue: Sealed secret not decrypting

**Symptoms**: Secret exists but application can't read values

**Solutions**:
```bash
# Check SealedSecret status
kubectl get sealedsecret -n <namespace>

# Check sealed-secrets controller logs
kubectl logs -n sealed-secrets-system deploy/sealed-secrets-controller

# Verify secret was created
kubectl get secret <app>-secret -n <namespace>

# Recreate sealed secret with correct namespace
```

## Related Documentation

- [Repository Structure Standards](/docs/standards/repository-structure.md) - Authoritative structure rules
- [Helm Best Practices](/.github/instructions/helm.instructions.md) - Helm chart configuration
- [Kustomize Patterns](/.github/instructions/kustomize.instructions.md) - Overlay management
- [Secret Management](/docs/security/README.md) - Sealed secrets procedures
- [Troubleshooting](/docs/troubleshooting/README.md) - Common issues and solutions

## See Also

- [Flux CD Documentation](https://fluxcd.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [Helm Documentation](https://helm.sh/docs/)
- [Conventional Commits](https://www.conventionalcommits.org/)
