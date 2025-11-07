# GitHub Copilot Agent Read-Only Cluster Access

## Overview

This configuration provides read-only Kubernetes cluster access for the GitHub Copilot coding agent. The Copilot agent runs on **self-hosted GitHub Actions runners inside the cluster** using ARC (Actions Runner Controller) and can investigate cluster resources to assist with troubleshooting and development.

## Architecture

Since the Kubernetes cluster is deployed in a **private network** and is **not reachable from GitHub-hosted runners**, this implementation uses:

1. **Actions Runner Controller (ARC)**: Self-hosted runners running inside the cluster
2. **In-Cluster ServiceAccount**: The runner pods use the `copilot-agent-readonly` ServiceAccount
3. **Direct Cluster Access**: Runners have direct access to the Kubernetes API server from within the cluster network

```
GitHub Copilot Agent
    │
    │ Triggered via GitHub Actions
    │
    ↓
Self-Hosted Runner (ARC) - Inside Cluster
    │
    │ Pod running with ServiceAccount: copilot-agent-readonly
    │ Mounted service account token at /var/run/secrets/kubernetes.io/serviceaccount/
    │
    ↓
Kubernetes API Server (In-Cluster)
    │
    └─ ClusterRole: copilot-agent-readonly (read-only permissions)
```

### Components

1. **Namespace**: `copilot-agent` - Dedicated namespace for RBAC resources
2. **ServiceAccount**: `copilot-agent-readonly` - Identity for the Copilot agent runners
3. **ClusterRole**: `copilot-agent-readonly` - Read-only permissions across all cluster resources
4. **ClusterRoleBinding**: Binds the ServiceAccount to the ClusterRole
5. **Secret**: `copilot-agent-readonly-token` - Service account token (automatically mounted in runner pods)
6. **Runner Scale Set**: `copilot-runner-set` - ARC runner scale set configured to use the ServiceAccount

### Security Model

- **Read-only access**: Only `get`, `list`, and `watch` verbs
- **No write permissions**: Cannot create, update, delete, or patch resources
- **No Secret data access**: Can only view Secret metadata, not the actual secret values
- **In-cluster only**: Runners operate within the cluster's private network
- **Comprehensive visibility**: Access to all cluster resources for investigation

## Permissions Granted

The Copilot agent has read-only access to:

- **Core resources**: Pods, Services, ConfigMaps, PersistentVolumes, Nodes, Events
- **Workload resources**: Deployments, StatefulSets, DaemonSets, ReplicaSets, Jobs, CronJobs
- **Flux CD resources**: GitRepositories, HelmRepositories, Kustomizations, HelmReleases, ImagePolicies
- **Security resources**: SealedSecrets (metadata only), Certificates, Issuers
- **Monitoring resources**: ServiceMonitors, PodMonitors, Prometheuses, AlertManagers
- **Networking resources**: Ingresses, NetworkPolicies, IngressClasses
- **Storage resources**: StorageClasses, VolumeAttachments
- **RBAC resources**: Roles, RoleBindings, ClusterRoles, ClusterRoleBindings (read-only)

## GitHub Actions Integration

The GitHub Copilot agent uses self-hosted runners via Actions Runner Controller (ARC):

1. **Runner Scale Set**: `copilot-runner-set` deployed in the `arc-runners` namespace
2. **In-Cluster Access**: Runner pods use the `copilot-agent-readonly` ServiceAccount
3. **Automatic Configuration**: The workflow automatically configures kubectl using the mounted service account token
4. **No External Secrets Needed**: All authentication happens via the in-cluster service account

### Workflow Configuration

The `.github/workflows/copilot-setup-steps.yml` workflow:

- **Runs on**: `copilot-runner-set` (self-hosted runner inside the cluster)
- **ServiceAccount**: Uses `copilot-agent-readonly` mounted by the runner pod
- **Cluster Access**: Direct access to `https://kubernetes.default.svc` from within the cluster
- **Verification**: Tests cluster access and confirms read-only permissions

## Usage

Once configured, the GitHub Copilot agent can:

```bash
# List all pods
kubectl get pods -A

# Check Flux resources
kubectl get hr -A
kubectl get kustomizations -A

# View logs
kubectl logs <pod-name> -n <namespace>

# Describe resources
kubectl describe deployment <name> -n <namespace>

# Check events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

## Setup Instructions

### 1. Deploy RBAC Resources

The RBAC resources are automatically deployed via Flux CD:

```bash
# Verify resources are deployed
kubectl get serviceaccount -n copilot-agent
kubectl get clusterrole copilot-agent-readonly
kubectl get clusterrolebinding copilot-agent-readonly
```

### 2. Deploy Copilot Runner Scale Set

The runner scale set is defined in [`apps/kyrion/copilot-runner-set.yaml`](../../../apps/kyrion/copilot-runner-set.yaml) and automatically deployed via Flux CD.

The runner pods are configured to:
- Use the `copilot-agent-readonly` ServiceAccount
- Run with read-only cluster access
- Have access to kubectl and other development tools

### 3. Verify Runner Deployment

Check that the runner scale set is deployed:

```bash
# Check the HelmRelease
kubectl get hr -n arc-runners copilot-runner-set

# Check runner pods (when a workflow is running)
kubectl get pods -n arc-runners -l actions.github.com/scale-set-name=copilot-runner-set
```

### 4. Test Workflow

The `copilot-setup-steps` workflow will automatically:
1. Run on the self-hosted runner inside the cluster
2. Configure kubectl using the mounted service account token
3. Verify read-only cluster access
4. Make cluster investigation capabilities available to Copilot

No additional secrets or configuration are needed!

## Troubleshooting

### Permission Denied Errors

If you see permission denied errors:
1. Verify the ClusterRole includes the necessary API groups and resources
2. Check the ClusterRoleBinding is correctly configured
3. Ensure the service account token is valid

### Connection Errors

If kubectl cannot connect to the cluster:
1. Verify the cluster API server URL is correct
2. Check the CA certificate is valid
3. Ensure the service account token is not expired

### Verify RBAC Permissions

Test what the service account can access:

```bash
# Check permissions
kubectl auth can-i --list --as=system:serviceaccount:copilot-agent:copilot-agent-readonly

# Test specific permissions
kubectl auth can-i get pods --as=system:serviceaccount:copilot-agent:copilot-agent-readonly
kubectl auth can-i create pods --as=system:serviceaccount:copilot-agent:copilot-agent-readonly
```

## Architecture Benefits

### Why Self-Hosted Runners with ARC?

1. **Private Network Access**: The cluster is not reachable from GitHub-hosted runners
2. **No External Secrets**: Service account tokens are automatically mounted in runner pods
3. **Secure**: Runners operate within the cluster's security boundary
4. **Cost Effective**: No need for VPNs or bastion hosts
5. **Scalable**: ARC automatically scales runners based on demand

### Comparison to Cloud-Based Approach

| Aspect | Self-Hosted (ARC) | Cloud-Based |
|--------|------------------|-------------|
| Cluster Access | ✅ Direct in-cluster | ❌ Not possible (private network) |
| Secret Management | ✅ Automatic (mounted SA token) | ❌ Requires external secrets |
| Network Setup | ✅ None needed | ❌ VPN/bastion required |
| Security | ✅ In-cluster security boundary | ⚠️ External access point |
| Cost | ✅ Uses cluster resources | ❌ GitHub-hosted runner costs |
| Scalability | ✅ Auto-scaling with ARC | ✅ Auto-scaling |

## Security Considerations

- The service account has broad read access across the cluster
- Secret content is not accessible, only metadata
- All operations are audited via Kubernetes audit logs
- The service account cannot make any modifications to the cluster
- Tokens should be rotated regularly

## Maintenance

### Updating Permissions

To add access to additional resources:

1. Edit `infrastructure/configs/copilot-agent-rbac/clusterrole.yaml`
2. Add the new API groups and resources with read-only verbs
3. Commit and push changes
4. Flux will automatically update the ClusterRole

### Rotating Tokens

To rotate the service account token:

```bash
# Delete the secret
kubectl delete secret copilot-agent-readonly-token -n copilot-agent

# Recreate it (Flux will sync from Git)
flux reconcile kustomization infra-configs
```

The service account token is automatically mounted in runner pods, so no GitHub secrets need to be updated.

## Related Documentation

- [GitHub Copilot Agent Environment Customization](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment)
- [Kubernetes RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes Service Account Tokens](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
