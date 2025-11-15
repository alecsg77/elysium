# Investigation Report: Issue #4 - Coder HelmRelease Timeout

## Summary
The Coder HelmRelease upgrade to version 2.28.3 is failing with "context deadline exceeded" due to insufficient memory on the node to support the rolling update strategy.

## Root Cause Analysis

### Primary Issue: Insufficient Memory for Rolling Update
The Coder deployment uses a `RollingUpdate` strategy which attempts to create new pods before terminating old ones. With each pod requesting 4Gi of memory, the upgrade process temporarily requires 8Gi total.

**Evidence:**
- Node capacity: 32Gi total memory
- Current node usage: 74% (23520Mi ≈ 23Gi)
- Available memory: ~9Gi
- Coder pod memory request: 4Gi per pod
- During rolling update: 2 pods × 4Gi = 8Gi required

### Kubernetes Events
```
0/1 nodes are available: 1 Insufficient memory.
preemption: 0/1 nodes are available: 1 No preemption victims found for incoming pod.
```

### HelmRelease Status
- **State**: Stalled (RetriesExceeded)
- **Error**: "Helm upgrade failed for release coder/coder-coder with chart coder@2.28.3: context deadline exceeded"
- **Upgrade Duration**: 5m0.413408917s (timed out)
- **Chart Version**: Attempting to upgrade from 2.28.1 → 2.28.3

### Current Pod Status
| Pod Name | Version | Status | Age |
|----------|---------|--------|-----|
| coder-78786899d9-nthwq | 2.28.1 | Running (1/1) | 4d21h |
| coder-5df88d876c-q5w9b | 2.28.3 | Pending (0/1) | 2d21h |

## Resolution Options

### Option 1: Use Recreate Deployment Strategy (Recommended for Single-Node)
**Pros:**
- Eliminates memory spike during upgrades
- Simpler resource management
- No risk of scheduling failures

**Cons:**
- Brief service downtime during pod replacement (~30-60 seconds)
- Users may experience temporary connection loss

**Implementation:**
Add to HelmRelease values:
```yaml
coder:
  deploymentStrategy:
    type: Recreate
```

### Option 2: Reduce Memory Request
**Pros:**
- Maintains zero-downtime rolling updates
- Better resource utilization

**Cons:**
- May cause OOM issues if Coder actually needs 4Gi
- Requires understanding of actual memory usage patterns

**Implementation:**
Add to HelmRelease values:
```yaml
coder:
  resources:
    requests:
      memory: 2Gi
    limits:
      memory: 4Gi
```

### Option 3: Increase Helm Timeout + Manual Intervention
**Pros:**
- No configuration changes needed
- Works if memory becomes available

**Cons:**
- Doesn't solve root cause
- Requires manual pod cleanup
- Unreliable solution

**Implementation:**
1. Delete the pending pod: `kubectl delete pod coder-5df88d876c-q5w9b -n coder`
2. Increase timeout in HelmRelease:
```yaml
spec:
  timeout: 10m
```

## Recommended Solution

**Use Option 1: Recreate Strategy**

For a single-node cluster with limited resources, the Recreate strategy is most appropriate. The brief downtime during upgrades is acceptable for a development environment like Coder workspaces.

### Implementation Steps

1. **Update HelmRelease Configuration**
   - File: `apps/base/coder/release.yaml` or `apps/kyrion/coder-values.yaml`
   - Add deployment strategy configuration

2. **Clean Up Failed State**
   - Delete the pending pod
   - Reset HelmRelease retry counter by suspending and resuming

3. **Verify Upgrade**
   - Monitor HelmRelease status
   - Confirm new pod reaches Running state
   - Test Coder accessibility

## Additional Observations

### Chart Version Policy
Current configuration uses `version: '*'` which auto-updates to latest versions. Consider:
- Pinning to specific versions for stability
- Using semver ranges (e.g., `2.28.x`) for controlled updates

### Resource Monitoring
Node is consistently at 74% memory usage. Consider:
- Regular monitoring of node resource capacity
- Planning for additional nodes or memory upgrades
- Implementing resource quotas per namespace

### Helm Timeout Configuration
Default 5-minute timeout may be too short for resource-constrained environments. Consider increasing to 10m for large applications.

## Files to Modify

1. **apps/base/coder/release.yaml** or **apps/kyrion/coder-values.yaml**
   - Add `deploymentStrategy.type: Recreate`
   - Optionally increase `spec.timeout`
   - Consider pinning chart version

## Validation Steps

After implementing the fix:

1. Check HelmRelease status:
   ```bash
   kubectl get hr coder -n coder
   flux get hr coder -n coder
   ```

2. Monitor pod status:
   ```bash
   kubectl get pods -n coder -w
   ```

3. Verify upgrade history:
   ```bash
   helm history coder-coder -n coder
   ```

4. Test Coder access:
   - Access URL: https://coder.flyingfox-tailor.ts.net
   - Verify workspaces are accessible

## Timeline

- **2025-11-10**: Last successful deployment (version 2.28.1)
- **2025-11-12 20:29:29**: Upgrade to 2.28.3 attempted
- **2025-11-12 20:34:29**: Upgrade failed after 5 minutes (timeout)
- **2025-11-12 21:26:46**: HelmRelease marked as Stalled (RetriesExceeded)
- **Current**: Old pod (2.28.1) still running, new pod (2.28.3) stuck in Pending

---

**Investigation completed**: 2025-11-15T18:15:03Z
**Investigator**: GitHub Copilot (troubleshooter agent)
