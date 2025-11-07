# GitHub Copilot Agent Read-Only Cluster Access

## Overview

This configuration provides read-only Kubernetes cluster access for the GitHub Copilot coding agent. The Copilot agent runs in a GitHub Actions environment and can investigate cluster resources to assist with troubleshooting and development.

## Architecture

### Components

1. **Namespace**: `copilot-agent` - Dedicated namespace for RBAC resources
2. **ServiceAccount**: `copilot-agent-readonly` - Identity for the Copilot agent
3. **ClusterRole**: `copilot-agent-readonly` - Read-only permissions across all cluster resources
4. **ClusterRoleBinding**: Binds the ServiceAccount to the ClusterRole
5. **Secret**: `copilot-agent-readonly-token` - Service account token for authentication

### Security Model

- **Read-only access**: Only `get`, `list`, and `watch` verbs
- **No write permissions**: Cannot create, update, delete, or patch resources
- **No Secret data access**: Can only view Secret metadata, not the actual secret values
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

The GitHub Copilot agent uses these credentials in the `copilot-setup-steps` workflow:

1. The workflow retrieves the service account token from the cluster
2. Configures kubectl with the token and cluster CA certificate
3. Copilot can now run kubectl commands with read-only access

### Workflow Configuration

The `.github/workflows/copilot-setup-steps.yml` workflow includes:

- **Cluster authentication**: Configures kubectl with the read-only service account
- **Verification step**: Tests cluster access is working
- **Security**: Uses encrypted secrets for cluster connection details

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

### 2. Retrieve Service Account Token

Get the service account token for GitHub Actions:

```bash
# Get the token
kubectl get secret copilot-agent-readonly-token -n copilot-agent -o jsonpath='{.data.token}' | base64 -d

# Get the cluster CA certificate
kubectl get secret copilot-agent-readonly-token -n copilot-agent -o jsonpath='{.data.ca\.crt}' | base64 -d
```

### 3. Configure GitHub Secrets

Add these secrets to your GitHub repository:

- `KUBE_TOKEN`: The service account token from step 2
- `KUBE_CA_CERT`: The cluster CA certificate from step 2
- `KUBE_SERVER`: Your cluster API server URL (e.g., `https://your-cluster:6443`)

### 4. Verify Access

The `copilot-setup-steps` workflow will automatically configure and test the cluster access.

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

Then update the `KUBE_TOKEN` secret in GitHub repository settings.

## Related Documentation

- [GitHub Copilot Agent Environment Customization](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment)
- [Kubernetes RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes Service Account Tokens](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
