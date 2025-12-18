# HelmRelease Recovery Procedures

This runbook provides systematic procedures for recovering from failed HelmRelease deployments in the cluster.

## Prerequisites

- Access to cluster via `kubectl` and `flux` CLI
- Familiarity with [Repository Structure Standards](/docs/standards/repository-structure.md)
- Understanding of [Cluster Architecture](/docs/architecture/cluster-architecture.md)

## Quick Reference

| Failure Type | Quick Fix | Full Procedure |
|--------------|-----------|----------------|
| **Timeout** | Increase `spec.timeout` | [Step 2](#step-2-common-failure-patterns-and-solutions) |
| **Values Error** | Validate with `helm template` | [Step 2](#step-2-common-failure-patterns-and-solutions) |
| **Chart Not Found** | Reconcile HelmRepository | [Step 2](#step-2-common-failure-patterns-and-solutions) |
| **CRD Missing** | Install CRDs first | [Step 2](#step-2-common-failure-patterns-and-solutions) |
| **MongoDB Failure** | Check PVC integrity | [Step 4](#step-4-persistent-mongodb-failures-librechat-example) |

## Recovery Procedure

### Step 1: Identify Failure Cause

```bash
# Check HelmRelease status
kubectl get hr -A

# Get detailed information
kubectl describe hr <name> -n <namespace>

# Check Helm release history
helm history <name> -n <namespace>

# View Helm controller logs
kubectl logs -n flux-system deploy/helm-controller | grep <namespace>/<name>
```

### Step 2: Common Failure Patterns and Solutions

#### Timeout

**Symptoms**: `Install/Upgrade timeout` error

**Resolution**:
1. Increase `spec.timeout` in HelmRelease
2. Check pod startup logs
3. Verify resource availability
4. Check init containers

**Example**:
```yaml
spec:
  timeout: 15m  # Increased from 5m default
```

#### Values Error

**Symptoms**: `Values validation failed` error

**Resolution**:
1. Validate values structure: `helm template <chart> -f values.yaml`
2. Check `valuesFrom` references exist
3. Compare with chart schema
4. Fix values and commit

#### Chart Not Found

**Symptoms**: `Chart not found` error

**Resolution**:
1. Verify HelmRepository is Ready
2. Check chart name spelling
3. Verify chart version exists
4. Update HelmRepository: `flux reconcile source helm <repo>`

#### CRD Missing

**Symptoms**: `CRD not found` error

**Resolution**:
1. Identify required CRDs
2. Install CRDs first via separate HelmRelease
3. Add `dependsOn` to main HelmRelease
4. Use `spec.install.crds: CreateReplace`

#### Dependency Not Ready

**Symptoms**: `Dependency not ready` error

**Resolution**:
1. Check dependency status
2. Fix dependency first
3. Wait for Ready condition
4. Flux will auto-retry

#### Image Pull Error

**Symptoms**: Pods in `ImagePullBackOff`

**Resolution**:
1. Verify image exists in registry
2. Check image pull secrets
3. Test registry access from cluster
4. Verify image tag

### Step 3: Force Remediation

#### Option A: Reconcile HelmRelease

```bash
# Force immediate reconciliation
flux reconcile helmrelease <name> -n <namespace>

# Watch status
watch kubectl get hr <name> -n <namespace>
```

#### Option B: Suspend and Resume

For persistent failures:

```bash
# Suspend to prevent retry loops
flux suspend helmrelease <name> -n <namespace>

# Fix underlying issue (update values, fix dependencies, etc.)
# Commit changes to Git

# Resume after fix
flux resume helmrelease <name> -n <namespace>
```

#### Option C: Manual Rollback

```bash
# View Helm release history
helm history <name> -n <namespace>

# Rollback to previous working version
helm rollback <name> <revision> -n <namespace>

# Update HelmRelease in Git to prevent re-upgrade
```

#### Option D: Delete and Recreate (Last Resort)

```bash
# Remove HelmRelease (keeps deployed resources)
kubectl delete hr <name> -n <namespace>

# Uninstall Helm release if needed
helm uninstall <name> -n <namespace>

# Fix configuration in Git
# Commit changes

# Recreate HelmRelease
flux reconcile kustomization apps
```

### Step 4: Persistent MongoDB Failures (LibreChat Example)

The `ai/librechat` HelmRelease historically fails with MongoDB container verification errors.

**Symptoms**:
- MongoDB pod in `CrashLoopBackOff`
- Container verification errors in logs
- PVC integrity issues

**Resolution**:

```bash
# Check MongoDB pod status
kubectl get pods -n ai -l app=mongodb

# View MongoDB logs
kubectl logs -n ai <mongodb-pod> --previous

# Common fixes:

# 1. Check persistent volume integrity
kubectl get pvc -n ai
kubectl describe pvc <mongodb-pvc> -n ai

# 2. Delete pod to force restart
kubectl delete pod -n ai <mongodb-pod>

# 3. If PV corrupted, delete PVC and recreate
kubectl delete pvc <mongodb-pvc> -n ai
# HelmRelease will recreate PVC automatically

# 4. Check MongoDB container image
# Verify image exists and is pullable
```

### Step 5: Validation After Recovery

```bash
# Verify HelmRelease is Ready
kubectl get hr <name> -n <namespace>

# Check deployed resources
kubectl get all -n <namespace>

# Check pod status
kubectl get pods -n <namespace>

# View application logs
kubectl logs -n <namespace> <pod-name>

# Test application endpoints
curl https://<app-url>
```

## Prevention Best Practices

### Deployment Configuration

- **Set appropriate timeouts**: Base on historical deployment times + 50% buffer
  ```yaml
  spec:
    timeout: 15m
  ```

- **Configure retry limits**:
  ```yaml
  spec:
    install:
      remediation:
        retries: 3
  ```

- **Enable automatic rollback**:
  ```yaml
  spec:
    upgrade:
      remediation:
        remediateLastFailure: true
  ```

### Development Workflow

- **Test in dev first**: Deploy to dev namespace before production
- **Pin chart versions**: Avoid `latest` tags
- **Validate locally**: Use `helm template` before committing
- **Monitor continuously**: Set up alerts for failed HelmReleases

### Common Mistakes to Avoid

❌ **Don't**:
- Use `latest` chart versions in production
- Skip validation of values structure
- Deploy without checking dependencies
- Ignore timeout warnings

✅ **Do**:
- Pin specific chart versions
- Validate with `helm template` before commit
- Check all dependencies are Ready
- Set realistic timeouts based on testing

## Troubleshooting Decision Tree

```
HelmRelease Failed
├─ Timeout?
│  ├─ Yes → Increase timeout, check pod logs
│  └─ No → Continue
├─ Values Error?
│  ├─ Yes → Validate with helm template
│  └─ No → Continue
├─ Chart Not Found?
│  ├─ Yes → Check HelmRepository, reconcile
│  └─ No → Continue
├─ CRD Missing?
│  ├─ Yes → Install CRDs, add dependency
│  └─ No → Continue
├─ Dependency Not Ready?
│  ├─ Yes → Fix dependency first
│  └─ No → Continue
└─ Image Pull Error?
   └─ Yes → Check registry, image tag, pull secrets
```

## Related Documentation

- [Application Deployment Runbook](/docs/runbooks/add-application.md)
- [Known Issues and Troubleshooting](/docs/troubleshooting/known-issues.md)
- [Repository Structure Standards](/docs/standards/repository-structure.md)
- [Cluster Architecture](/docs/architecture/cluster-architecture.md)

## References

- [Flux HelmRelease Documentation](https://fluxcd.io/flux/components/helm/helmreleases/)
- [Helm Documentation](https://helm.sh/docs/)
