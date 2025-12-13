# Known Issues and Troubleshooting

This knowledge base documents common cluster problems, their symptoms, root causes, and verified resolutions.

**Last Updated**: 2025-01-24

## How to Use

1. **Search** for your issue by component or error message
2. **Check symptoms** to confirm it matches your situation
3. **Try the documented resolution** first
4. **Create a troubleshooting issue** if resolution doesn't work or issue is different

## Issue Categories

- [Flux CD](#flux-cd)
- [Kubernetes](#kubernetes)
- [Helm](#helm)
- [Storage](#storage)
- [Applications](#applications)

---

## Flux CD

### HelmRelease Install Timeout

**Symptoms**:
- HelmRelease stuck in `InstallFailed` state
- Retries exhausted message
- Pods stuck in `ImagePullBackOff`

**Root Cause**: Default timeout (5m) insufficient for large container images (> 5GB)

**Resolution**:
1. Check actual image pull duration in pod events
2. Calculate: actual time + 50% buffer
3. Update HelmRelease `spec.timeout`:
   ```yaml
   spec:
     timeout: 15m
   ```
4. Reconcile: `flux reconcile helmrelease <name> -n <namespace>`

**Validation**:
```bash
flux get hr <name> -n <namespace>  # Should show Ready=True
kubectl get pods -n <namespace>  # Should show Running
```

**Related**: [Coder HelmRelease timeout](/docs/troubleshooting/coder-helmrelease-timeout.md)

---

### Variable Substitution Failed

**Symptoms**:
- Kustomization reconciliation fails
- Error: `variable ${VAR_NAME} not found`

**Root Cause**: Referenced ConfigMap or Secret doesn't exist, or key name mismatch

**Resolution**:
1. Verify Kustomization `postBuild.substituteFrom` references
2. Check ConfigMap/Secret exists: `kubectl get cm,secret -n flux-system`
3. Verify key names match exactly (case-sensitive)
4. Create missing ConfigMap: `kubectl create cm cluster-vars --from-literal=VAR_NAME=value -n flux-system`
5. For secrets, use `kubeseal` to create SealedSecret

**Validation**:
```bash
flux get kustomization <name>  # Ready=True
kubectl get cm cluster-vars -n flux-system -o yaml  # Verify variable
```

---

### GitRepository Not Syncing

**Symptoms**:
- GitRepository stuck on old commit SHA
- Status: Failed
- Checkout error message

**Root Cause**: Network issues, SSH key problems, or branch doesn't exist

**Resolution**:
1. Verify SSH key: `kubectl get secret flux-system -n flux-system`
2. Check branch exists in repository
3. Force reconciliation: `flux reconcile source git flux-system`
4. If SSH key expired, regenerate and update secret

**Validation**:
```bash
flux get sources git  # Ready=True with recent commit
```

---

## Kubernetes

### Pod CrashLoopBackOff - Missing ConfigMap

**Symptoms**:
- Pod in `CrashLoopBackOff`
- Logs show: `configmap not found` or `file not found: /config/...`

**Root Cause**: Pod references ConfigMap that doesn't exist or isn't mounted

**Resolution**:
1. Check pod spec for `configMapRef` or volume references
2. Verify ConfigMap exists: `kubectl get cm -n <namespace>`
3. If missing, create ConfigMap in app source directory
4. Add to `kustomization.yaml` resources list
5. Commit and wait for Flux reconciliation

**Validation**:
```bash
kubectl get cm -n <namespace>  # ConfigMap should exist
kubectl get pods -n <namespace>  # Pods should be Running
kubectl logs -n <namespace> <pod>  # No config errors
```

---

### ImagePullBackOff Error

**Symptoms**:
- Pod stuck in `ImagePullBackOff`
- Event: `Failed to pull image` or `image not found`

**Root Cause**: Image doesn't exist, wrong tag, or registry auth failure

**Resolution**:
1. Verify image exists in container registry
2. Check image tag in HelmRelease or deployment
3. If private registry, ensure `imagePullSecret` configured
4. Check `ImagePolicy` if using Flux image automation
5. Update image tag to valid version

**Validation**:
```bash
kubectl describe pod -n <namespace> <pod>  # Check events
kubectl get pods -n <namespace>  # Running
```

---

## Helm

### Chart Installation Failure

**Symptoms**:
- HelmRelease shows `InstallFailed`
- Values validation errors
- CRD not found errors

**Root Cause**: Chart version doesn't exist, invalid values, or missing CRDs

**Resolution**:
1. Verify chart exists: `helm search repo <repo>/<chart>`
2. Validate values against chart: `helm template <chart> -f values.yaml`
3. Check chart dependencies are installed first
4. For CRD errors, install CRDs separately via dependency HelmRelease

**Validation**:
```bash
helm list -n <namespace>  # Release listed and deployed
kubectl get pods -n <namespace>  # Resources created
```

---

## Storage

### PersistentVolumeClaim Pending

**Symptoms**:
- PVC stuck in `Pending`
- Pod can't mount volume
- No error message

**Root Cause**: StorageClass doesn't exist or node doesn't have capacity

**Resolution**:
1. Check StorageClass exists: `kubectl get sc`
2. Verify PVC has correct `storageClassName`
3. Check node capacity: `kubectl describe node <node>`
4. For `existingClaim` pattern, verify PVC was pre-created

**Validation**:
```bash
kubectl get pvc -n <namespace>  # Status: Bound
kubectl get pv  # PersistentVolume created
```

---

## Applications

### LibreChat MongoDB Connection Failure

**Symptoms**:
- LibreChat pods restart every 2 minutes
- Logs: `MongoDB connection failed`
- MongoDB pod in `CrashLoopBackOff`

**Root Cause**: MongoDB PVC corrupted, pod failing health check, or memory constraints

**Resolution**:
1. Check MongoDB pod logs: `kubectl logs -n ai <mongodb-pod> --previous`
2. Check PVC integrity: `kubectl get pvc -n ai`
3. If PVC corrupted, delete PVC to force recreation
4. Check memory requests vs node availability (See [resource optimization](/docs/runbooks/resource-optimization.md))
5. Delete failed pod: `kubectl delete pod -n ai <mongodb-pod>`

**Validation**:
```bash
kubectl get pods -n ai -l app=mongodb  # Running (1/1)
kubectl get pods -n ai -l app=librechat  # Ready and Running
```

---

## Reporting New Issues

When none of the above match your situation:

1. Gather diagnostics:
   ```bash
   kubectl get all -n <namespace>
   kubectl describe pod <pod> -n <namespace>
   kubectl logs <pod> -n <namespace> --tail=100
   flux get hr -A
   kubectl get events -n <namespace> --sort-by='.lastTimestamp'
   ```

2. Create a [troubleshooting issue](https://github.com/alecsg77/elysium/issues/new/choose)

3. Include:
   - Component (Flux/Kubernetes/Application/Network/Other)
   - Namespace and resource names
   - Exact error messages
   - Recent changes
   - Diagnostic output (redacted for secrets)
