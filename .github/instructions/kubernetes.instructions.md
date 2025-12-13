---
applyTo: "**/*.yaml,**/*.yml"
description: "Kubernetes manifest best practices for GitOps"
---

# Kubernetes Manifest Guidelines

## General Principles
- Follow GitOps principles: all cluster state declared in Git
- Use declarative configuration exclusively (no imperative kubectl commands)
- Ensure idempotency: manifests should be safe to apply multiple times
- Prefer Kustomize overlays over duplicated manifests
- Use labels consistently for resource organization and selection

## Resource Naming and Organization
- Use lowercase kebab-case for all resource names (e.g., `my-app-service`)
- Include namespace prefix in multi-tenant resources
- Group related resources in the same directory
- Use descriptive names that indicate purpose and environment

## Namespace Management
- Always specify namespace explicitly in manifests
- Use namespace labels for policy enforcement and monitoring
- Include standard labels: `app.kubernetes.io/name`, `app.kubernetes.io/instance`, `app.kubernetes.io/component`
- Add custom labels for GitOps tracking: `kustomize.toolkit.fluxcd.io/name`, `kustomize.toolkit.fluxcd.io/namespace`

## Security Best Practices
- Never commit plain text secrets to Git (use Sealed Secrets)
- Use ServiceAccounts with minimal RBAC permissions
- Set security contexts for pods: runAsNonRoot, readOnlyRootFilesystem
- Define resource limits and requests for all containers
- Use NetworkPolicies to restrict pod-to-pod communication

## Resource Specifications
- Always define resource requests and limits
- Set appropriate liveness and readiness probes
- Use meaningful probe paths and timeouts
- Configure graceful shutdown with preStop hooks
- Set appropriate pod disruption budgets for high availability

## ConfigMap and Secret Management
- Use ConfigMaps for non-sensitive configuration
- Reference ConfigMaps and Secrets via environment variables or volume mounts
- Avoid embedding large configuration files inline; use volumes instead
- Version configuration changes through Git commits

## Storage and Persistence
- Use PersistentVolumeClaims with appropriate storage classes
- Specify storage requirements explicitly
- Use volume mount propagation appropriately
- Consider using CSI drivers for cloud storage integration

## Ingress and Networking
- Use Ingress resources for HTTP/HTTPS routing
- Leverage IngressClass for multiple ingress controllers
- Configure TLS certificates via cert-manager annotations
- Use appropriate backend protocol annotations

## Monitoring and Observability
- Add Prometheus annotations for scraping: `prometheus.io/scrape`, `prometheus.io/port`, `prometheus.io/path`
- Use PodMonitor or ServiceMonitor CRDs for advanced scraping
- Include health check endpoints in all applications
- Add structured logging with consistent format

## Dependency Management
- Use `dependsOn` in Flux Kustomizations for ordered deployment
- Declare dependencies explicitly in HelmRelease specs
- Wait for CRDs to be established before deploying CRs
- Use health checks and readiness gates appropriately

## YAML Formatting
- Use 2-space indentation consistently
- Separate logical sections with blank lines
- Order fields logically: metadata, spec, status
- Use `---` document separator between multiple resources
- Validate YAML syntax before committing

## Web-Based Troubleshooting

### Issue-Based Diagnostic Workflow

For pod failures, CrashLoopBackOff, ImagePullBackOff, or resource issues, use GitHub Issues with structured templates:

1. **Create Bug Report**: https://github.com/alecsg77/elysium/issues/new/choose
   - Select "🐛 Bug Report" template for known issues
   - Select "🔍 Troubleshooting Request" for investigation
   - Provide pod name, namespace, error messages, recent changes

2. **Invoke Copilot Diagnostics**: In GitHub Copilot Chat on issue page
   ```
   #file:.github/agents/troubleshooter.agents.md
   Please run Kubernetes pod diagnostics for namespace <namespace>
   ```

3. **Automated Diagnostic Collection**:
   - **Pod Status**: Get pod conditions, phase, container states
   - **Logs**: Extract recent logs and error patterns from containers
   - **Events**: Timeline of Kubernetes events for pod lifecycle
   - **Resource Status**: CPU/memory requests, limits, and actual usage
   - **Configuration**: ConfigMap/Secret references, volume mounts
   - **Network**: Service endpoints, ingress routes, network policies

4. **Root Cause Categories**:
   - **Image Issues**: ImagePullBackOff, invalid image tag, registry authentication
   - **Configuration Errors**: Missing ConfigMap/Secret, invalid volume mounts
   - **Resource Constraints**: OOMKilled, CPU throttling, node pressure
   - **Health Check Failures**: Liveness/readiness probe timeouts or failures
   - **Networking**: DNS resolution, service discovery, network policy blocks
   - **Dependencies**: Database unavailable, external API unreachable

5. **Automated Resolution**: After approval, coding agent fixes issues and coordinator validates

### Common Kubernetes Issue Patterns (from Knowledge Base)

**Pod CrashLoopBackOff (Missing ConfigMap)**:
- **Symptom**: `CreateContainerConfigError`, pod restarting
- **Root Cause**: Referenced ConfigMap doesn't exist in namespace
- **Resolution**: Create missing ConfigMap in `apps/base/<app>/` or `clusters/kyrion/config-map.yaml`
- **Validation**: `kubectl get pods -n <namespace>` shows Running status

**ImagePullBackOff**:
- **Symptom**: `ErrImagePull` or `ImagePullBackOff` status
- **Root Cause**: Image doesn't exist, wrong tag, or registry authentication failure
- **Resolution**: Verify image exists, check image pull secrets, test registry access
- **Validation**: Pod enters Running state

**OOMKilled (Out of Memory)**:
- **Symptom**: Pod restarting with `OOMKilled` reason
- **Root Cause**: Memory usage exceeds container limit
- **Resolution**: Increase `resources.limits.memory` in HelmRelease values or manifest
- **Validation**: Pod runs without restarts, `kubectl top pod` shows memory under limit

**GPU Allocation Failure**:
- **Symptom**: Pod pending with `Insufficient gpu.intel.com/i915`
- **Root Cause**: No GPU-enabled nodes or GPU already allocated
- **Resolution**: Verify GPU device plugin running, check node GPU capacity
- **Validation**: Pod scheduled and running with GPU allocated

**Persistent Volume Claim Pending**:
- **Symptom**: PVC stuck in Pending state
- **Root Cause**: No StorageClass available or insufficient capacity
- **Resolution**: Create StorageClass or provision storage on nodes
- **Validation**: `kubectl get pvc -n <namespace>` shows Bound status

### Diagnostic Commands Reference

Quick commands for manual troubleshooting:

```bash
# Pod status and events
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Container logs
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -c <container-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous  # Previous container instance

# Resource usage
kubectl top pods -n <namespace>
kubectl top nodes

# Configuration inspection
kubectl get configmaps -n <namespace>
kubectl get secrets -n <namespace>
kubectl describe cm <configmap-name> -n <namespace>

# Service and networking
kubectl get svc -n <namespace>
kubectl get endpoints -n <namespace>
kubectl get ingress -n <namespace>
kubectl describe ingress <ingress-name> -n <namespace>

# Debugging with ephemeral containers
kubectl debug <pod-name> -n <namespace> -it --image=busybox
```

### Integration with Automated Resolution

**Circuit Breaker Protection**:
- Prevents infinite retry loops with 3-attempt limit per bug
- Tracks attempts via `resolution-attempt:N` labels
- Triggers manual intervention after 3 failures
- Reset with `/reset-attempts` command after manual fixes

**Validation Workflow**:
- After PR merge, coordinator monitors pod status for 10 minutes
- Checks pod phase, container readiness, restart count, events
- **Success**: Marks issue resolved, updates knowledge base
- **Failure**: Generates new resolution plan (if < 3 attempts) or escalates

### Knowledge Base Search

Search for known fixes before creating issues:

```bash
# Search by component
grep -A 20 "## Kubernetes" docs/troubleshooting/known-issues.md

# Search by error pattern
grep -i "crashloopbackoff" docs/troubleshooting/known-issues.md
grep -i "imagepullbackoff" docs/troubleshooting/known-issues.md
grep -i "oomkilled" docs/troubleshooting/known-issues.md

# Search by resource type
grep -A 20 "Pod\|Deployment\|StatefulSet" docs/troubleshooting/known-issues.md
```

### Additional Resources

- **Troubleshooting Guide**: [Web-Based Troubleshooting Workflow](/docs/troubleshooting/web-troubleshooting.md) - Complete workflow examples
- **Known Issues**: [Known Issues and Troubleshooting](/docs/troubleshooting/known-issues.md) - Searchable database of past resolutions
- **Troubleshooter Agent**: `.github/agents/troubleshooter.agents.md` - Diagnostic collection
- **Issue Coordinator**: `.github/agents/issue-coordinator.agents.md` - Resolution orchestration
- **Knowledge Base Agent**: `.github/agents/knowledge-base.agents.md` - Pattern matching
