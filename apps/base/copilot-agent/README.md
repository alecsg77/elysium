# GitHub Copilot Agent - Read-Only Cluster Access

## Overview

This deployment provides a GitHub Copilot agent running inside the Kubernetes cluster with read-only permissions. The agent can be used to investigate and troubleshoot cluster resources without the ability to make changes.

## Architecture

### Components

- **Namespace**: `copilot-agent`
- **ServiceAccount**: `copilot-agent` with cluster-wide read-only access
- **ClusterRole**: `copilot-agent-readonly` with comprehensive read permissions
- **Deployment**: Single pod running `bitnami/kubectl` image

### Security Features

- ✅ **Read-Only Access**: Only `get`, `list`, and `watch` verbs
- ✅ **Non-Root Execution**: Runs as user ID 1000
- ✅ **No Privilege Escalation**: `allowPrivilegeEscalation: false`
- ✅ **Read-Only Filesystem**: Root filesystem is read-only
- ✅ **Dropped Capabilities**: All Linux capabilities dropped
- ✅ **Resource Limits**: CPU and memory limits enforced
- ✅ **SecComp Profile**: Runtime default seccomp profile applied

## Permissions

The agent has read-only access to:

### Core Resources
- Pods, Services, ConfigMaps, PersistentVolumes
- Nodes, Namespaces, Events, ResourceQuotas
- ServiceAccounts

### Workload Resources
- Deployments, DaemonSets, ReplicaSets, StatefulSets
- Jobs, CronJobs

### Networking Resources
- Ingresses, NetworkPolicies, IngressClasses

### GitOps Resources (Flux CD)
- GitRepositories, HelmRepositories, HelmCharts
- Kustomizations, HelmReleases
- ImageRepositories, ImagePolicies, ImageUpdateAutomations
- Alerts, Providers, Receivers

### Security Resources
- SealedSecrets (metadata only, not the encrypted data)
- Certificates, CertificateRequests, Issuers

### Monitoring Resources
- ServiceMonitors, PodMonitors
- Prometheuses, AlertManagers, PrometheusRules

### RBAC Resources
- Roles, RoleBindings, ClusterRoles, ClusterRoleBindings (read-only)

## Usage

### Accessing the Agent

To access the agent pod and use kubectl:

```bash
# Get the pod name
kubectl get pods -n copilot-agent

# Exec into the agent pod
kubectl exec -it -n copilot-agent deployment/copilot-agent -- bash
```

### Example Commands

Once inside the agent pod, you can run kubectl commands:

```bash
# List all pods across all namespaces
kubectl get pods -A

# List all Flux HelmReleases
kubectl get hr -A

# Describe a specific resource
kubectl describe pod <pod-name> -n <namespace>

# View logs from a pod
kubectl logs <pod-name> -n <namespace>

# Get Flux Kustomizations status
kubectl get kustomizations -A

# View events in a namespace
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Check deployment status
kubectl get deployments -A

# View resource usage (if metrics-server is installed)
kubectl top pods -A
kubectl top nodes
```

### Using with GitHub Copilot

This agent can be used to provide GitHub Copilot with cluster context for better troubleshooting and investigation:

1. **Investigation**: Execute commands to gather cluster state information
2. **Troubleshooting**: Examine logs, events, and resource status
3. **Analysis**: Review Flux CD resources and GitOps state
4. **Monitoring**: Check resource metrics and health

## Limitations

### What the Agent CAN do:
- ✅ Read all cluster resources (except secrets)
- ✅ View logs from pods
- ✅ Check resource status and health
- ✅ Investigate Flux CD GitOps resources
- ✅ View events and metrics

### What the Agent CANNOT do:
- ❌ Create, update, or delete any resources
- ❌ Execute commands in other pods (no pod/exec)
- ❌ Read Secret data (only metadata)
- ❌ Modify cluster configuration
- ❌ Access node filesystem
- ❌ Perform privileged operations

## Resource Requirements

- **CPU Request**: 50m
- **CPU Limit**: 200m
- **Memory Request**: 64Mi
- **Memory Limit**: 256Mi

## Health Checks

The deployment includes:
- **Liveness Probe**: Checks kubectl client every 30 seconds
- **Readiness Probe**: Checks kubectl client every 10 seconds

## Deployment

This agent is deployed as part of the GitOps workflow via Flux CD:

1. The manifests are defined in `apps/base/copilot-agent/`
2. Flux automatically deploys the agent to the cluster
3. The agent starts and remains running for cluster access

## Troubleshooting

### Agent pod not starting

Check the pod status and events:
```bash
kubectl get pods -n copilot-agent
kubectl describe pod -n copilot-agent <pod-name>
kubectl logs -n copilot-agent <pod-name>
```

### Permission denied errors

The agent only has read-only access. If you see permission errors, verify:
1. The command only requires read access (get, list, watch)
2. The ClusterRole includes the necessary API groups and resources
3. The ClusterRoleBinding is correctly configured

### Agent pod is stuck

If the agent pod is stuck or not ready:
```bash
# Check pod events
kubectl describe pod -n copilot-agent deployment/copilot-agent

# Check logs
kubectl logs -n copilot-agent deployment/copilot-agent

# Restart the pod
kubectl rollout restart deployment/copilot-agent -n copilot-agent
```

## Security Considerations

- The agent has broad read access across the cluster
- Secret content is not accessible, only metadata
- All operations are audited via Kubernetes audit logs
- The agent cannot make any modifications to the cluster
- Resource limits prevent resource exhaustion attacks

## Maintenance

### Updating the Agent

To update the agent image or configuration:

1. Modify the deployment manifest in `apps/base/copilot-agent/deployment.yaml`
2. Commit and push changes to Git
3. Flux will automatically apply the updates

### Adding Additional Permissions

If you need to add read access to additional resources:

1. Edit `apps/base/copilot-agent/clusterrole.yaml`
2. Add the new API groups and resources
3. Commit and push changes
4. Flux will automatically update the ClusterRole

**Note**: Always maintain read-only access principles. Never add write, create, update, or delete verbs.

## Related Documentation

- [Kubernetes RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Flux CD Documentation](https://fluxcd.io/docs/)
- [kubectl Command Reference](https://kubernetes.io/docs/reference/kubectl/)

## Support

For issues or questions about the copilot-agent deployment:

1. Check pod logs: `kubectl logs -n copilot-agent deployment/copilot-agent`
2. Review cluster events: `kubectl get events -n copilot-agent`
3. Verify RBAC permissions: `kubectl auth can-i --list --as=system:serviceaccount:copilot-agent:copilot-agent`
