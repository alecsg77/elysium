# Elysium: GitOps-Managed Kubernetes Homelab

## Architecture Overview
This is a **GitOps-driven Kubernetes homelab** using Flux CD for declarative cluster management. The repository structure follows a layered approach with strict dependency ordering:

### Repository Structure
- **`clusters/kyrion/`** - Flux configuration for the `kyrion` cluster (bootstrap entry point)
  - `apps.yaml` - Main application Kustomization (depends on infra-configs)
  - `infrastructure.yaml` - Infrastructure controllers and configs
  - `monitoring.yaml` - Observability stack deployment
  - `sealed-secrets.yaml` - Cluster-wide encrypted secrets
  - `flux-system/` - Flux CD bootstrap configuration
- **`apps/`** - Application deployments using base/overlay pattern
  - `base/` - Shared application configurations and HelmReleases
  - `kyrion/` - Environment-specific patches and configurations
- **`infrastructure/`** - Core cluster infrastructure (ordered deployment)
  - `controllers/` - Kubernetes operators and controllers
  - `configs/` - Cluster-wide configurations and policies
- **`monitoring/`** - Observability stack (Prometheus, Grafana, Loki, Tempo, Jaeger)
  - `controllers/` - Monitoring operators and CRDs
  - `configs/` - Dashboards, datasources, and monitoring configs
- **`coder/`** - Development workspace templates for Coder.com platform
- **`functions/`** - Serverless functions using Fission framework

### Flux CD Components
The cluster uses Flux with **image-reflector-controller** and **image-automation-controller** for automated image updates:
- **Source Controller**: Manages Git, OCI, Bucket, and Helm sources
- **Kustomize Controller**: Applies Kustomize manifests with dependency management
- **Helm Controller**: Manages HelmReleases with values from ConfigMaps/Secrets
- **Image Controllers**: Scans registries and updates image tags automatically
- **Notification Controller**: Webhooks and alerts for GitOps events

## Key Patterns and Best Practices

### GitOps with Flux CD
- **Bootstrap Command**: `./scripts/bootstrap_flux.sh` (sets up SSH keys and GitHub integration)
- **Repository Monitoring**: Flux monitors `main` branch with 1h interval, 5m retry
- **Dependency Chain**: `infra-controllers → infra-configs → apps` and `monitoring-controllers → monitoring-configs`
- **Variable Substitution**: Uses `postBuild.substituteFrom` with cluster ConfigMaps/Secrets
  - `cluster-secret-vars` (Secret) - encrypted values like tokens, passwords
  - `cluster-vars` (ConfigMap) - non-sensitive environment variables
- **Secrets Management**: All secrets encrypted using Bitnami Sealed Secrets (public key: `etc/certs/pub-sealed-secrets.pem`)

### Application Deployment Pattern
```yaml
# Standard app structure in apps/base/<app>/
├── kustomization.yaml      # Base resources and dependencies
├── namespace.yaml          # Namespace definition with labels
├── release.yaml           # HelmRelease (for single-app directories like coder)
│   OR individual files    # Separate YAML files per service (like arkham/)
└── ts-ingress.yaml        # Optional Tailscale ingress for private access
```

### Flux Resource Management
When analyzing or troubleshooting Flux resources:

#### HelmRelease Analysis
1. Check HelmRelease status: `kubectl get hr -A` or use `get_kubernetes_resources`
2. Examine the `spec.chart.sourceRef` to find the source (HelmRepository/GitRepository)
3. Verify source readiness and revision matching
4. Check `valuesFrom` references to ConfigMaps/Secrets
5. Review `status.conditions` for detailed error information
6. Look at managed resources in `status.inventory`

#### Kustomization Analysis  
1. Check Kustomization status and dependencies: `flux get kustomizations -A`
2. Examine `sourceRef` (typically GitRepository named `flux-system`)
3. Verify source revision and path accuracy
4. Check `substituteFrom` references for variable substitution
5. Review managed resources in inventory for individual resource health

#### Source Analysis
1. GitRepository sources should show ready condition with latest commit SHA
2. HelmRepository sources should reflect chart availability
3. Check source intervals and reconciliation timestamps
4. Verify authentication for private repositories

### Helm + Kustomize Integration
- **Base Pattern**: Most apps use HelmReleases in `apps/base/` pointing to `onechart` repository
- **Environment Patches**: Kyrion-specific overrides in `apps/kyrion/` using Kustomize patches
- **Values Management**: 
  - Base values in HelmRelease spec
  - Environment patches modify specific paths
  - External values from ConfigMaps/Secrets via `valuesFrom`
- **Image Updates**: Automated via Flux ImageUpdateAutomation with policy annotations:
  ```yaml
  # In HelmRelease values:
  image: 
    tag: "1.0.0" # {"$imagepolicy": "namespace:image-policy"}
  ```

### Secret Management Best Practices
- **CRITICAL**: Never commit plain text secrets to the repository
- **Cluster-wide Secrets**: Stored in `clusters/kyrion/sealed-secrets.yaml`
  - Contains essential cluster variables and authentication tokens
  - Referenced by Flux Kustomizations via `postBuild.substituteFrom`
- **App-specific Secrets**: Created in respective app directories as sealed-secret.yaml
- **Creation Workflow**:
  ```bash
  # Create sealed secret (requires kubeseal CLI + cluster access)
  echo -n "secret-value" | kubectl create secret generic app-secret \
    --dry-run=client --from-file=key=/dev/stdin -o yaml | \
    kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml > sealed-secret.yaml
  ```
- **Variable Substitution**: Use `${VARIABLE_NAME}` syntax in manifests
- **Security Model**: Public key encryption allows committing encrypted secrets safely

### Development Workflows

#### Creating/Modifying Apps
1. Add base configuration in `apps/base/<app>/`
2. Add app to `apps/base/kustomization.yaml` resources
3. Create environment-specific patches in `apps/kyrion/` if needed
4. Commit changes - Flux will auto-deploy

#### Managing Secrets
```bash
# Create sealed secret (requires kubeseal CLI + cluster access)
echo -n "secret-value" | kubectl create secret generic app-secret --dry-run=client --from-file=key=/dev/stdin -o yaml | kubeseal -o yaml > sealed-secret.yaml
```

#### Advanced Flux Operations
- **Force Reconciliation**: `flux reconcile source git flux-system`
- **Suspend/Resume**: `flux suspend/resume kustomization <name>`
- **Debug Failed Deployments**: Check events, conditions, and inventory status
- **Image Policy Updates**: Monitor ImageUpdateAutomation commits for automated updates
- **Dependency Analysis**: Review `dependsOn` chains in Kustomizations

#### Coder Development Environment
- Templates in `coder/templates/` for different dev environments
- Kubernetes-based workspaces with persistent volumes
- DevContainer support via envbuilder for standardized environments

#### Function Development
- FaaS using Fission framework in `functions/` directory
- Deploy with: `cd functions && fission spec apply -n default --delete --wait`
- Auto-deployed via GitHub Actions on function changes

### Infrastructure Components

#### Core Services (infrastructure/)
- **Tailscale**: Private network overlay for secure access
- **Traefik**: Ingress controller with automatic HTTPS via cert-manager
- **Sealed Secrets**: Encrypted secret management
- **CSI-rclone**: Cloud storage integration

#### Media Stack (apps/base/arkham/)
- Plex media server with Intel GPU transcoding
- *arr stack (Radarr, Sonarr, Bazarr, Prowlarr) for media automation
- QBittorrent for downloads with VPN integration

#### Key Configuration Patterns
- Resource requests/limits use Intel GPU devices: `gpu.intel.com/i915: "1"`
- Persistent volumes via `existingClaim: pvc-storage` pattern
- Tailscale ingresses for private access: `ts.net` domain
- Environment variables injected from cluster ConfigMaps/Secrets
- **Init containers**: Apps requiring external mounts use wait scripts for mount detection

### CI/CD Automation
- **Flux Updates**: Daily automated updates via `.github/workflows/update-flux.yml`
- **Function Deploy**: Auto-deploy functions on changes to `functions/` directory
- **Coder Templates**: Publish templates to Coder registry on changes

### Debugging & Operations
- Access cluster via `etc/kubeconfig` file
- Monitor Flux with: `flux get all -A` 
- Check HelmRelease status: `kubectl get hr -A`
- View sealed secret decryption: `kubectl get secret <name> -o yaml`

### Troubleshooting Workflows

#### Flux HelmRelease Issues
1. **Check HelmRelease Status**: `kubectl get hr -A` - look for Ready condition
2. **Analyze Source Dependencies**: Examine `spec.chart.sourceRef` or `spec.chartRef`
3. **Verify HelmRepository/GitRepository**: Check source readiness and authentication
4. **Review Values Sources**: If `valuesFrom` exists, verify referenced ConfigMaps/Secrets
5. **Examine Managed Resources**: Check `status.inventory` for failed resources
6. **Container Analysis**: Get pod logs for failed workloads
7. **Root Cause Report**: Document findings with specific error messages

#### Flux Kustomization Issues
1. **Check Kustomization Status**: `flux get kustomizations -A` - verify Ready condition
2. **Source Verification**: Ensure GitRepository source is accessible and up-to-date
3. **Path Validation**: Confirm `spec.path` points to valid directory structure
4. **Substitution Problems**: Verify `substituteFrom` ConfigMaps/Secrets exist and contain required keys
5. **Dependency Chain**: Check `dependsOn` relationships are satisfied
6. **Resource Conflicts**: Examine inventory for resource ownership conflicts

#### General Flux Debugging
1. **Controller Health**: Check flux-system namespace pod status
2. **Source Connectivity**: Verify network access to Git repositories and registries
3. **RBAC Issues**: Ensure service accounts have required permissions
4. **Resource Limits**: Check if controllers are hitting memory/CPU limits
5. **Webhook Problems**: Verify notification controller and receiver configurations

### Critical File References
- **Flux entry point**: `clusters/kyrion/apps.yaml`
- **App definitions**: `apps/kyrion/kustomization.yaml` 
- **Infrastructure config**: `infrastructure/configs/kustomization.yaml`
- **Cluster secrets**: `clusters/kyrion/sealed-secrets.yaml`
- **Image policies**: Search for `imageupdateautomation.yaml`

## Flux Custom Resource Definitions (CRDs)

When working with Flux resources, understand these key CRDs:

### Source Controller CRDs
- **GitRepository**: Points to Git repositories containing Kubernetes manifests or Helm charts
- **OCIRepository**: References OCI artifacts (container registry stored manifests/charts)
- **Bucket**: S3-compatible storage sources
- **HelmRepository**: Helm chart repositories
- **HelmChart**: Individual chart references from repositories

### Kustomize Controller CRDs  
- **Kustomization**: Builds and applies Kubernetes manifests from sources with dependency management

### Helm Controller CRDs
- **HelmRelease**: Manages Helm chart deployments with values injection and lifecycle management

### Image Automation CRDs
- **ImageRepository**: Scans container registries for available image tags
- **ImagePolicy**: Defines rules for selecting latest/suitable image versions
- **ImageUpdateAutomation**: Automatically updates Git repository with new image references

### Notification Controller CRDs
- **Provider**: Notification destinations (Slack, Discord, webhooks)
- **Alert**: Event filtering and forwarding rules
- **Receiver**: Webhook endpoints for triggering reconciliation

## Operational Best Practices

### Flux Reconciliation Management
- **Manual Reconciliation**: `flux reconcile source git flux-system` (forces immediate sync)
- **Suspend Operations**: `flux suspend kustomization <name>` (pause automatic updates)
- **Resume Operations**: `flux resume kustomization <name>` (restart automatic updates)
- **Status Monitoring**: `flux get all -A` (comprehensive status overview)

### Resource Dependency Patterns
The cluster follows this dependency hierarchy:
1. **Infrastructure Controllers** (`infra-controllers`) - Operators and CRDs
2. **Infrastructure Configs** (`infra-configs` dependsOn infra-controllers) - Cluster policies  
3. **Applications** (`apps` dependsOn infra-configs) - User workloads
4. **Monitoring Controllers** (`monitoring-controllers`) - Monitoring operators (independent)
5. **Monitoring Configs** (`monitoring-configs` dependsOn monitoring-controllers) - Dashboards and config

### Image Update Automation
- **Update Interval**: 10m scanning interval via `ImageUpdateAutomation`
- **Commit Pattern**: Automated commits with structured messages
- **Policy Annotations**: Use `{"$imagepolicy": "namespace:policy-name"}` in manifests
- **Branch Protection**: Updates committed directly to main branch (consider branch protection)

When modifying this codebase, always consider the GitOps principle: the cluster state should match this repository exactly.

### External Storage Dependencies
- **Media Library Mount**: Azure storage via rclone with systemd automount (can take minutes to mount)
