# Elysium: GitOps-Managed Kubernetes Homelab

> **Note**: This repository has specialized Copilot instructions, prompts, and chat modes. See [README-COPILOT.md](README-COPILOT.md) for usage guide.

## Architecture Overview

This is a **GitOps-driven Kubernetes homelab** using Flux CD for declarative cluster management. The repository structure follows a layered approach with strict dependency ordering.

### Technology Stack
- **GitOps**: Flux CD v2 with image automation
- **Orchestration**: Kubernetes (K3s)
- **Package Management**: Helm 3 + Kustomize
- **Secrets**: Bitnami Sealed Secrets
- **Ingress**: Traefik with cert-manager
- **Networking**: Tailscale for private access
- **Monitoring**: Prometheus, Grafana, Loki, Tempo
- **Storage**: Local storage + rclone CSI for cloud

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
The cluster uses Flux CD v2 with **image-reflector-controller** and **image-automation-controller** for automated image updates:

| Controller | Purpose | Key Features |
|------------|---------|--------------|
| **Source Controller** | Manages sources | Git, OCI, Bucket, Helm repositories |
| **Kustomize Controller** | Applies manifests | Dependency management, health checks, pruning |
| **Helm Controller** | Manages releases | Values injection, lifecycle hooks, rollbacks |
| **Image Reflector** | Scans registries | Image tag discovery, policy evaluation |
| **Image Automation** | Updates Git | Automated commits for image updates |
| **Notification Controller** | Alerting | Webhooks, events, receivers |

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

#### ⚠️ CRITICAL SECURITY RULES
- **NEVER** commit plain text secrets to the repository
- **ALWAYS** use Sealed Secrets for sensitive data
- **VERIFY** secrets are encrypted before committing
- **ROTATE** secrets regularly (quarterly recommended)
- **AUDIT** secret access in application logs

#### Secret Types
| Type | Location | Purpose | Reference Method |
|------|----------|---------|------------------|
| **Cluster-wide** | `clusters/kyrion/sealed-secrets.yaml` | Cluster variables, tokens | `postBuild.substituteFrom` |
| **App-specific** | `apps/base/<app>/*-sealed-secret.yaml` | App credentials, API keys | `valuesFrom` in HelmRelease |
| **ConfigMaps** | `clusters/kyrion/config-map.yaml` | Non-sensitive config | `postBuild.substituteFrom` |

#### Sealed Secret Creation Workflow
```bash
# Create sealed secret (requires kubeseal CLI + cluster access)
echo -n "secret-value" | kubectl create secret generic app-secret \
  --namespace=<namespace> \
  --dry-run=client --from-file=key=/dev/stdin -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > sealed-secret.yaml
```

#### Variable Substitution
- Use `${VARIABLE_NAME}` syntax in manifests
- Reference in Kustomization: `postBuild.substituteFrom`
- Flux replaces variables during reconciliation
- **Security Model**: Public key encryption allows safe Git commits

#### Secret Reference Patterns
```yaml
# In HelmRelease - reference Secret via valuesFrom
spec:
  valuesFrom:
    - kind: Secret
      name: app-secret
      valuesKey: values.yaml

# In Pod - reference Secret as environment variable
env:
  - name: API_KEY
    valueFrom:
      secretKeyRef:
        name: app-secret
        key: api-key

# In Kustomization - use for variable substitution
spec:
  postBuild:
    substituteFrom:
      - kind: Secret
        name: cluster-secret-vars
```

#### Troubleshooting Secrets
- **Secret not decrypted**: Check sealed-secrets controller logs
- **Wrong namespace**: Recreate with correct namespace
- **Variable not substituted**: Verify ConfigMap/Secret exists and key name matches
- **Permission denied**: Check RBAC for service account

> **Tip**: Use `@workspace #file:manage-secrets.prompt.md` for guided secret creation

### Development Workflows

#### Creating/Modifying Apps
1. **Plan**: Use planner chat mode or `#file:deploy-app.prompt.md`
2. **Create base**: Add configuration in `apps/base/<app>/`
   - `namespace.yaml` - Namespace with labels
   - `release.yaml` or individual YAML files
   - `kustomization.yaml` - Resource list
   - `*-sealed-secret.yaml` - Encrypted secrets
3. **Add to base**: Update `apps/base/kustomization.yaml` resources
4. **Create overlay**: Add environment patches in `apps/kyrion/` if needed
5. **Commit**: Push to Git - Flux auto-deploys within 5 minutes
6. **Verify**: Check status with `flux get hr -A` or `kubectl get pods -n <namespace>`
7. **Document**: Create README using `#file:generate-docs.prompt.md`

#### Managing Secrets
**Quick Reference**:
```bash
# Generic secret
kubectl create secret generic app-secret \
  --namespace=<namespace> \
  --from-literal=key=value \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml > sealed-secret.yaml

# From file
kubectl create secret generic app-config \
  --namespace=<namespace> \
  --from-file=config.yaml \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml > sealed-secret.yaml

# Docker registry
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com \
  --docker-username=user \
  --docker-password=pass \
  --namespace=<namespace> \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml > sealed-secret.yaml
```

> **Guided workflow**: `@workspace #file:manage-secrets.prompt.md create secret`

#### Advanced Flux Operations
| Operation | Command | Use Case |
|-----------|---------|----------|
| **Force Reconciliation** | `flux reconcile source git flux-system` | Immediate Git sync |
| **Reconcile Kustomization** | `flux reconcile kustomization apps` | Deploy changes now |
| **Reconcile HelmRelease** | `flux reconcile hr <name> -n <namespace>` | Update single app |
| **Suspend Kustomization** | `flux suspend kustomization <name>` | Pause auto-updates |
| **Resume Kustomization** | `flux resume kustomization <name>` | Restart auto-updates |
| **View Events** | `flux events --for Kustomization/<name>` | See reconciliation history |
| **Diff Changes** | `flux diff kustomization apps --path clusters/kyrion` | Preview changes |
| **Build Local** | `flux build kustomization apps --path clusters/kyrion` | Test locally |

#### Common Development Commands
```bash
# Validate YAML syntax
yamllint clusters/ apps/ infrastructure/ monitoring/

# Build Kustomize overlays locally
kustomize build apps/kyrion/
kustomize build infrastructure/controllers/

# Test Helm template rendering
helm template <name> <chart> -f values.yaml

# Validate Kubernetes resources
kubectl apply --dry-run=client -f manifest.yaml

# Check Flux system health
flux check

# Monitor Flux resources
flux get all -A
watch -n 5 'flux get kustomizations -A'
watch -n 5 'kubectl get hr -A'
```

#### Debugging Workflows
When things go wrong:
1. **Use troubleshooter chat mode** or `#file:troubleshoot-flux.prompt.md`
2. **Check Flux status**: `flux get all -A`
3. **Review logs**: `kubectl logs -n flux-system deploy/<controller-name>`
4. **Examine resources**: `kubectl describe <resource> <name> -n <namespace>`
5. **View events**: `kubectl get events -n <namespace> --sort-by='.lastTimestamp'`
6. **Root cause**: Document findings for future reference

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

> **Quick Help**: Switch to troubleshooter chat mode or use `@workspace #file:troubleshoot-flux.prompt.md`

#### Troubleshooting Decision Tree
```
Issue Reported
├─ Flux System Healthy? (flux check)
│  ├─ No → Check controller pods, logs, resources
│  └─ Yes → Continue
├─ Kustomization Failed? (flux get kustomizations -A)
│  ├─ Yes → Check Git source, path, dependencies, variables
│  └─ No → Continue
├─ HelmRelease Failed? (kubectl get hr -A)
│  ├─ Yes → Check chart source, values, CRDs, timeouts
│  └─ No → Continue
├─ Pod Not Running? (kubectl get pods -A)
│  ├─ Yes → Check logs, events, resources, probes
│  └─ No → Continue
└─ Service Unreachable?
   └─ Yes → Check service, endpoints, ingress, network policies
```

#### Flux HelmRelease Issues
| Step | Action | Command |
|------|--------|---------|
| 1. Check status | Verify Ready condition | `kubectl get hr -A` |
| 2. Describe | Get detailed info | `kubectl describe hr <name> -n <namespace>` |
| 3. Check source | Verify chart source | `flux get sources helm -A` |
| 4. Check values | Verify ConfigMaps/Secrets | `kubectl get cm,secret -n <namespace>` |
| 5. View inventory | Check managed resources | `kubectl get hr <name> -n <namespace> -o yaml \| yq '.status.inventory'` |
| 6. Check pods | Get pod status | `kubectl get pods -n <namespace>` |
| 7. View logs | Check application logs | `kubectl logs -n <namespace> <pod-name>` |

**Common HelmRelease Errors**:
- `Install failed: timeout exceeded` → Increase timeout or check pod startup
- `Chart not found` → Verify chart name, version, and repository
- `Values validation failed` → Check values structure matches chart schema
- `CRDs not found` → Install CRDs first via dependency

#### Flux Kustomization Issues
| Step | Action | Command |
|------|--------|---------|
| 1. Check status | Verify Ready condition | `flux get kustomizations -A` |
| 2. Check source | Verify Git access | `flux get sources git -A` |
| 3. Validate path | Confirm directory exists | Check repository structure |
| 4. Check variables | Verify substitution sources | `kubectl get cm,secret -n flux-system` |
| 5. Review dependencies | Check dependency chain | Look at `dependsOn` field |
| 6. Check inventory | View managed resources | `flux get kustomization <name> -o yaml` |

**Common Kustomization Errors**:
- `Path not found` → Verify `spec.path` points to valid directory
- `Variable substitution failed` → Check ConfigMap/Secret exists and contains key
- `Dependency not ready` → Wait for dependency or fix dependency issue
- `YAML parse error` → Validate YAML syntax with yamllint

#### General Flux Debugging
**System Health Checks**:
```bash
# Check Flux installation
flux check

# Check all controllers running
kubectl get pods -n flux-system

# Check controller logs
kubectl logs -n flux-system deploy/source-controller --tail=100
kubectl logs -n flux-system deploy/kustomize-controller --tail=100
kubectl logs -n flux-system deploy/helm-controller --tail=100

# Check resource usage
kubectl top pods -n flux-system

# Check recent events
kubectl get events -n flux-system --sort-by='.lastTimestamp'
```

**Common Root Causes**:
1. **Network issues**: Can't reach GitHub or Helm repositories
2. **Authentication**: SSH key or credentials invalid
3. **YAML syntax**: Invalid YAML in manifests
4. **Dependencies**: Resources deployed out of order
5. **Resource limits**: Controllers OOMKilled or throttled
6. **API versions**: Deprecated APIs used in manifests

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

### GitOps Principles

When modifying this codebase, always follow these GitOps principles:

1. **Git as Single Source of Truth**: All cluster state defined in this repository
2. **Declarative Configuration**: Use YAML manifests, not imperative commands
3. **Automated Deployment**: Flux automatically syncs Git to cluster
4. **Version Control**: All changes tracked via Git commits
5. **Auditability**: Git history provides complete audit trail
6. **Rollback Capability**: Revert Git commits to rollback changes
7. **Environment Separation**: Use Kustomize overlays for environment-specific config

### Quality Standards

#### Before Committing
- [ ] YAML syntax valid (`yamllint`)
- [ ] Kustomize builds successfully (`kustomize build`)
- [ ] Helm templates render correctly (`helm template`)
- [ ] No plain text secrets
- [ ] Resource limits defined
- [ ] Health probes configured
- [ ] Documentation updated
- [ ] Changes tested locally

#### Code Review Checklist
Use reviewer chat mode or `#file:review-config.prompt.md` to verify:
- [ ] Security best practices followed
- [ ] Kubernetes conventions adhered to
- [ ] Flux patterns correctly implemented
- [ ] Dependencies properly declared
- [ ] Secrets encrypted with Sealed Secrets
- [ ] Resources appropriately sized
- [ ] Documentation complete

### External Dependencies

#### Storage
- **Media Library**: Azure Blob Storage via rclone CSI
  - Mount path: `/mnt/media-library`
  - Automount may take 2-5 minutes on pod start
  - Apps using external storage should have init containers with mount detection
  - Example: Apps in `arkham` namespace wait for mount before starting

#### Network
- **Tailscale**: Private network overlay for secure access
  - Ingress class: `tailscale`
  - Domain: `*.ts.net`
  - Apps with `ts-ingress.yaml` accessible privately
  
#### Image Registries
- **Docker Hub**: Public images (rate-limited)
- **GitHub Container Registry**: Private images (authenticated)
- **Custom Registry**: `arkham.docker.local` for local builds

### Maintenance Tasks

#### Weekly
- Review Flux reconciliation status
- Check for failed deployments
- Review image update commits
- Monitor resource usage

#### Monthly
- Update Flux components
- Review and rotate secrets
- Update Helm charts to latest versions
- Review and clean unused resources

#### Quarterly
- Kubernetes version upgrade
- Security audit and vulnerability scan
- Review and update documentation
- Backup sealed-secrets private key

### Support and Resources

#### Quick Help
- **Deploy app**: `@workspace #file:deploy-app.prompt.md`
- **Debug issue**: Switch to troubleshooter chat mode
- **Review config**: `@workspace #file:review-config.prompt.md`
- **Manage secrets**: `@workspace #file:manage-secrets.prompt.md`
- **Generate docs**: `@workspace #file:generate-docs.prompt.md`

#### Documentation
- **Copilot Guide**: `.github/README-COPILOT.md`
- **Instructions**: `.github/instructions/*.instructions.md`
- **Prompts**: `.github/prompts/*.prompt.md`
- **Chat Modes**: `.github/chatmodes/*.chatmode.md`

#### External Resources
- [Flux Documentation](https://fluxcd.io/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)

---

**Remember**: This is a GitOps repository. All cluster changes must go through Git. Use the Copilot tools and instructions to maintain consistency and follow best practices.
