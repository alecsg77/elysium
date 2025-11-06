---
mode: 'agent'
model: Claude Sonnet 4
tools: ['codebase', 'fetch']
description: 'Troubleshoot Flux GitOps deployment issues'
---

# Troubleshoot Flux Deployment

You are helping diagnose and fix Flux CD GitOps deployment issues in the Elysium Kubernetes homelab.

## Diagnostic Process

### Step 1: Check Flux System Health
```bash
# Check Flux component status
flux check

# View all Flux resources
flux get all -A

# Check Flux controller logs
kubectl logs -n flux-system deploy/source-controller
kubectl logs -n flux-system deploy/kustomize-controller
kubectl logs -n flux-system deploy/helm-controller
```

### Step 2: Identify Failed Resources

**For Kustomizations:**
```bash
# Check Kustomization status
flux get kustomizations -A

# Get detailed status
kubectl describe kustomization <name> -n flux-system

# View events
kubectl get events -n flux-system --sort-by='.lastTimestamp'
```

**For HelmReleases:**
```bash
# Check HelmRelease status
kubectl get hr -A

# Get detailed status
kubectl describe hr <name> -n <namespace>

# Check Helm release history
helm history <name> -n <namespace>
```

### Step 3: Check Source Status

**GitRepository:**
```bash
# Verify Git source is ready
flux get sources git -A

# Check source synchronization
kubectl describe gitrepository flux-system -n flux-system
```

**HelmRepository:**
```bash
# Verify Helm repository is accessible
flux get sources helm -A

# Check repository status
kubectl describe helmrepository <name> -n flux-system
```

### Step 4: Analyze Common Issues

#### Issue: Kustomization Failed to Apply
- **Check path**: Verify `spec.path` in Kustomization points to valid directory
- **Check syntax**: Validate YAML syntax in target directory
- **Check variables**: Verify ConfigMaps/Secrets referenced in `substituteFrom` exist
- **Check dependencies**: Ensure `dependsOn` resources are ready

#### Issue: HelmRelease Failed to Install
- **Check chart source**: Verify HelmRepository or GitRepository is accessible
- **Check chart version**: Confirm chart version exists in repository
- **Check values**: Validate values structure matches chart expectations
- **Check CRDs**: Ensure required CRDs are installed first

#### Issue: Secret Substitution Failed
- **Check sealed secret**: Verify sealed secret exists and is unsealed
- **Check variable syntax**: Ensure `${VARIABLE}` format is correct
- **Check substituteFrom**: Verify ConfigMap/Secret names are correct
- **Check key names**: Confirm variable keys exist in source

#### Issue: Dependency Not Ready
- **Check dependency chain**: Review `dependsOn` relationships
- **Check health**: Verify dependency resources are healthy
- **Check timing**: May need to adjust reconciliation intervals

### Step 5: Force Reconciliation
```bash
# Reconcile Git source
flux reconcile source git flux-system

# Reconcile specific Kustomization
flux reconcile kustomization <name>

# Reconcile HelmRelease
flux reconcile helmrelease <name> -n <namespace>
```

### Step 6: Examine Resource Status
```bash
# Check created resources
kubectl get all -n <namespace>

# Check resource events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Check pod logs
kubectl logs -n <namespace> <pod-name>

# Check pod status
kubectl describe pod -n <namespace> <pod-name>
```

## Resolution Strategies

### For YAML Syntax Errors
1. Run local validation: `kustomize build <path>`
2. Fix syntax errors in manifests
3. Commit and push changes
4. Wait for Flux to reconcile or force reconciliation

### For Value Substitution Issues
1. Check variable definitions in cluster ConfigMap/Secret
2. Verify variable references match exactly (case-sensitive)
3. Update variables if needed
4. Restart Flux controllers if caching issues suspected

### For Image Pull Failures
1. Check image exists in specified registry
2. Verify image pull secrets are configured
3. Check network connectivity to registry
4. Validate image tag or digest

### For Resource Conflicts
1. Identify conflicting resource with `kubectl get <resource> -A`
2. Determine ownership (check labels and annotations)
3. Remove conflict or adjust configuration
4. Prune stale resources with `flux reconcile ks <name> --prune`

### For Failed Health Checks
1. Check readiness and liveness probes
2. Verify application is starting correctly
3. Check resource constraints (CPU/memory)
4. Review application logs for startup errors

## Debugging Commands Reference

```bash
# Suspend reconciliation for investigation
flux suspend kustomization <name>

# Resume reconciliation
flux resume kustomization <name>

# Export Kustomization build
flux build kustomization <name> --path <path>

# Diff current state vs Git
flux diff kustomization <name>

# Export HelmRelease values
helm get values <name> -n <namespace>

# Render Helm template locally
helm template <name> <chart> -f values.yaml

# Check sealed secret decryption
kubectl get secret <name> -n <namespace> -o yaml
```

## Common Root Causes

1. **Typos in resource names or namespaces**
2. **Missing dependencies (CRDs not installed)**
3. **Invalid Helm chart values structure**
4. **Secrets not encrypted or not decrypted**
5. **Network issues accessing Git or Helm repositories**
6. **Resource limits causing OOMKills**
7. **API version deprecation/removal**
8. **Dependency ordering issues**

Refer to [Flux troubleshooting guide](../.github/instructions/flux.instructions.md#error-handling) for more details.
