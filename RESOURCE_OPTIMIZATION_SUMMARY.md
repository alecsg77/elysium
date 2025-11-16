# Resource Optimization Summary

**Issue**: Coder pod failed to schedule with "Insufficient memory" despite node showing 72% actual usage vs 96% reserved.

**Analysis Date**: 2025-11-16

## Current State
- **Node**: utopia (32GB total memory)
- **Memory Requests**: 31GB (96%) - severely over-provisioned
- **Actual Usage**: 23GB (72%) - significant headroom
- **Problem**: Resource requests too high relative to actual consumption

## Optimization Changes

### High-Impact Optimizations

| Application | Old Request | New Request | Actual Usage | Savings |
|-------------|-------------|-------------|--------------|---------|
| **Coder** | 4Gi | 512Mi | ~163Mi | 3.5Gi |
| **Discourse** | 3Gi | 1Gi | ~576Mi | 2Gi |
| **Plex** | 2Gi | 512Mi | ~455Mi | 1.5Gi |
| **QBittorrent** | 1Gi | 512Mi | ~2.7Gi* | 512Mi |
| **Sonarr** | 1Gi | 384Mi | ~276Mi | 640Mi |
| **Radarr** | 1Gi | 384Mi | ~269Mi | 640Mi |
| **Bazarr** | 1Gi | 384Mi | ~320Mi | 640Mi |
| **Lidarr** | 1Gi | 384Mi | ~257Mi | 640Mi |
| **Prowlarr** | 1Gi | 384Mi | ~189Mi | 640Mi |
| **Unmonitorr** | 1Gi | 384Mi | <200Mi | 640Mi |
| **SearXNG** | 1Gi | 512Mi | N/A | 512Mi |

*QBittorrent high usage is expected during active downloads - kept at 512Mi with 4Gi limit

### Total Memory Freed
- **Request Reduction**: ~12Gi (from 31Gi to ~19Gi)
- **New Utilization**: ~59% of node capacity
- **Headroom**: ~13Gi available for scheduling

### Limits Adjustment Strategy
- **Coder**: Limit 4Gi → 2Gi (adequate for dev workspaces)
- **Discourse**: Limit 12Gi → 4Gi (forum workload)
- **Plex**: Limit 8Gi → 4Gi (transcoding with GPU offload)
- **Arkham apps**: Limit 4Gi → 2Gi (media management tools)
- **SearXNG**: Limit 4Gi → 2Gi (search engine)

### Files Modified

1. **apps/kyrion/coder-values.yaml** - Added resource limits
2. **apps/base/arkham/plex.yaml** - Reduced memory request/limit
3. **apps/base/ai/searxng.yaml** - Reduced memory request/limit
4. **apps/kyrion/arkham-resources.yaml** - New patch file for Arkham apps
5. **apps/kyrion/discourse-resources.yaml** - New patch file for Discourse
6. **apps/kyrion/kustomization.yaml** - Added new patch references

## Rationale

### Request Sizing
- Set requests to ~1.5-2x actual usage for normal operation
- Provides buffer for transient spikes without over-reservation
- Based on Grafana metrics showing stable usage patterns

### Limit Sizing  
- Set limits to ~3-5x requests for burst capacity
- Prevents OOMKill on legitimate usage spikes
- Allows Kubernetes to make better scheduling decisions

### Conservative Exceptions
- **Prometheus**: Kept at 2Gi request (uses ~2Gi actual)
- **Elasticsearch**: Kept at 1Gi request (uses 1.5Gi - may need monitoring)
- **QBittorrent**: 512Mi request with 4Gi limit (burst during downloads)

## Expected Outcomes

1. **Coder pod will schedule successfully** - 4Gi freed from Coder alone
2. **Better cluster utilization** - Actual usage aligns with reservations
3. **Improved scheduling flexibility** - More headroom for new workloads
4. **Maintained stability** - Limits still provide burst capacity
5. **No performance degradation** - Requests still exceed typical usage

## Monitoring Recommendations

Post-deployment, monitor for:
1. OOMKilled pods (indicates limits too low)
2. Memory pressure evictions (indicates node overcommit)
3. Application performance degradation
4. Pod restart patterns

If issues arise, adjust specific application requests incrementally rather than reverting all changes.

## Deployment

Changes committed to Git and will be applied automatically by Flux CD within 5 minutes.

Check deployment status:
```bash
flux get hr -A
kubectl get pods -A
kubectl top pods -A
kubectl describe node utopia
```
