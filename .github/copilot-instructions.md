# Elysium: GitOps-Managed Kubernetes Homelab

Welcome to the Elysium Kubernetes homelab! This document serves as a comprehensive guide for understanding, developing, and maintaining the GitOps-managed Kubernetes cluster using Flux CD.

## Architecture Overview

This is a **GitOps-driven Kubernetes homelab** using Flux CD for declarative cluster management. The repository structure follows a layered approach with strict dependency ordering.

### Network Architecture
- **Private Network**: Kubernetes cluster is deployed in a private network with internet access
- **Not Cloud-Accessible**: Cluster is not reachable from GitHub-hosted runners or public internet
- **Self-Hosted Runners**: GitHub Copilot agent runs on self-hosted runners inside the cluster using ARC (Actions Runner Controller)
- **Cluster Access**: Copilot agent has direct access to the Kubernetes API server from within the cluster network

#### Network Integration Components
- **Tailscale Mesh**: Private overlay network for secure cluster access
  - Ingress class: `tailscale`
  - Domain suffix: `*.ts.net`
  - DNS configuration via `ts-dns` resource
  - Default proxy class: `ts-default-proxy-class`
- **Traefik Ingress**: HTTP/HTTPS routing and TLS termination
  - IngressRoute resources for HTTP routing
  - TLSOption resources for TLS configuration
  - cert-manager integration for automatic certificate provisioning
  - Traefik Hub features enabled
- **Azure Arc Integration**: Hybrid cloud management (optional)
  - Namespaces: `azure-arc`, `azure-arc-release`
  - Arc Workload Identity for Azure service authentication
  - Namespace: `arc-workload-identity`
  - Monitoring integration via `arc-workload-identity-monitor`
- **Actions Runner Controller (ARC)**: GitHub Actions self-hosted runners
  - Namespaces: `arc-runners`, `arc-system`
  - Runner sets: `coder`, `copilot`, `fission`, `raiplaysoundrss`
  - Scales runners based on GitHub Actions job demand
  - Kubernetes-native runner lifecycle management

### Technology Stack
- **GitOps**: Flux CD v2 with image automation
- **Orchestration**: Kubernetes (K3s)
- **Package Management**: Helm 3 + Kustomize
- **Secrets**: Bitnami Sealed Secrets
- **Ingress**: Traefik with cert-manager
- **Networking**: Tailscale for private access
- **Monitoring**: Prometheus, Grafana, Loki, Tempo, OpenTelemetry, Elasticsearch, Jaeger, Minio
- **Storage**: Local storage + rclone CSI for cloud
- **CI/CD**: Actions Runner Controller (ARC) for self-hosted GitHub Actions runners

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
- **`monitoring/`** - Observability stack (Prometheus, Grafana, Loki, Tempo, Jaeger, Elasticsearch, OpenTelemetry)
  - `controllers/` - Monitoring operators and CRDs
    - `kube-prometheus-stack/` - Prometheus Operator, Grafana, Alertmanager
    - `loki-stack/` - Log aggregation with Loki and Promtail
    - `tempo-stack/` - Distributed tracing backend
    - `opentelemetry/` - OpenTelemetry Operator and Collector
    - `elastic/` - Elasticsearch for log indexing and Jaeger storage
    - `pushprox/` - Prometheus proxy for metrics behind firewalls
  - `configs/` - Dashboards, datasources, and monitoring configs
    - `dashboards/` - Grafana dashboards for cluster and application metrics
    - `datasources/` - Prometheus, Loki, Tempo, Jaeger data source configurations
    - `podmonitor.yaml` - PodMonitor resources for application metrics
    - `otel.yaml` - OpenTelemetry pipeline configuration
    - `elasticsearch.yaml` - Elasticsearch cluster and index configurations

**Monitoring Architecture**:
- **Metrics**: Prometheus scrapes metrics, Grafana visualizes, Alertmanager handles alerts
- **Logs**: Promtail ships logs to Loki, Elasticsearch indexes for Jaeger
- **Traces**: OpenTelemetry Collector receives traces, forwards to Tempo and Jaeger
- **Storage**: Minio provides S3-compatible storage for Loki and Tempo blocks
- **`coder/`** - Development workspace templates for Coder.com platform
- **`functions/`** - Serverless functions using Fission framework

### AI/ML Workload Stack (apps/base/ai/)
The cluster hosts a comprehensive AI/ML infrastructure in the `ai` namespace:

| Application | Purpose | Key Features |
|------------|---------|-------------|
| **Ollama** | LLM inference server | Local model hosting, GPU acceleration |
| **Open WebUI** | Web interface for LLMs | Chat interface, prompt management |
| **LibreChat** | Multi-model chat platform | OpenAI-compatible API, conversation management |
| **LocalAI** | OpenAI-compatible API | Local model inference, multiple backends |
| **SearXNG** | Privacy-focused metasearch | AI context gathering, web search integration |

**Hardware Acceleration**: AI workloads utilize Intel GPU resources (`gpu.intel.com/i915`) for inference acceleration.

**Common Issues**:
- **LibreChat MongoDB**: Historically fails with container verification errors - check MongoDB pod logs and persistent volume integrity
- **GPU allocation**: Ensure Intel GPU device plugin is running and devices are available
- **Model downloads**: Large models may cause slow startup - check init container logs

### Namespace Organization

The cluster uses 25+ namespaces for logical separation:

| Category | Namespaces | Purpose |
|----------|------------|---------|
| **System** | `kube-system`, `kube-public`, `kube-node-lease`, `default` | Kubernetes core components |
| **Flux** | `flux-system`, `capacitor` | GitOps controllers and image automation |
| **Infrastructure** | `cert-manager`, `tailscale`, `sealed-secrets-system` | Core infrastructure services |
| **Networking** | `traefik`, `ingress` | Ingress and traffic management |
| **Storage** | `csi-rclone` | Storage provisioners and drivers |
| **Monitoring** | `monitoring`, `elastic-system`, `opentelemetry-operator-system` | Observability stack |
| **CI/CD** | `arc-system`, `arc-runners` | GitHub Actions runner infrastructure |
| **Azure** | `azure-arc`, `azure-arc-release`, `arc-workload-identity` | Azure Arc hybrid management (optional) |
| **Applications** | `ai`, `arkham`, `coder`, `fission`, `n8n`, `discourse`, `registry`, `romm`, `mediamtx`, `raiplaysoundrss` | User workloads |
| **Development** | `airflow`, `error-pages` | Development and utility applications |
| **Upgrades** | `system-upgrade` | K3s automatic upgrade controller |
| **Device Plugins** | `intel-device-plugins-system` | Hardware device management |

**Namespace Conventions**:
- System namespaces: Reserved by Kubernetes
- Infrastructure: Cluster-wide services with elevated privileges
- Application: Isolated workloads with specific RBAC
- Monitoring: Read-only access to cluster metrics and logs

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

### Flux Status Detection

**Note on Flux Instance Detection**: Some Flux tooling may report "No Flux instance found" even when Flux is fully operational. This is a detection limitation, not an actual failure.

**How to Verify Flux is Actually Running**:
1. **Check Flux controllers**: `kubectl get pods -n flux-system`
   - Should show: source-controller, kustomize-controller, helm-controller, image-reflector-controller, image-automation-controller, notification-controller
2. **Check Flux resources**: `kubectl get kustomizations -A` and `kubectl get hr -A`
   - Should show your Kustomizations and HelmReleases with status
3. **Check Git synchronization**: `kubectl get gitrepositories -n flux-system`
   - Should show flux-system GitRepository with Ready status and recent commit SHA
4. **Use Flux CLI**: `flux get all -A`
   - Should display all Flux resources across namespaces

**If these commands show healthy resources, Flux is working correctly** despite detection tool warnings.

**Common False Positive Scenarios**:
- Flux installed via non-standard methods (manual manifests vs. flux bootstrap)
- Flux resources in unexpected namespaces
- Flux version incompatibility with detection tools
- Custom Flux component names or labels

See the [Flux Troubleshooting Runbook](#flux-troubleshooting-runbook) for detailed diagnostic procedures.

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

### Image Update Automation Patterns

The cluster uses Flux image automation to keep container images up-to-date:

#### Image Update Architecture
- **ImageRepository**: Scans container registries for available tags (10m interval)
- **ImagePolicy**: Defines version selection rules (semver, regex, alphabetical)
- **ImageUpdateAutomation**: Commits image tag updates to Git repository

#### Common ImagePolicy Patterns

**Semantic Versioning (Recommended)**:
```yaml
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: app-policy
  namespace: app-namespace
spec:
  imageRepositoryRef:
    name: app-image
  policy:
    semver:
      range: '>=1.0.0 <2.0.0'  # Major version 1.x
```

**Numeric Ordering** (for date-based tags):
```yaml
spec:
  policy:
    numerical:
      order: asc  # or desc for latest
```

**Alphabetical Ordering** (for branch tags):
```yaml
spec:
  policy:
    alphabetical:
      order: asc
```

**Regex Filtering** (for complex tag patterns):
```yaml
spec:
  filterTags:
    pattern: '^main-[a-f0-9]+-(?P<ts>[0-9]+)$'
    extract: '$ts'
  policy:
    numerical:
      order: asc
```

#### Image Policy Marker in Manifests

Add policy marker comments to image tags in HelmRelease values:
```yaml
spec:
  values:
    image:
      repository: ghcr.io/org/app
      tag: 1.0.0 # {"$imagepolicy": "app-namespace:app-policy"}
```

**ImageUpdateAutomation will**:
1. Scan ImageRepository for new tags matching ImagePolicy
2. Update the tag value in the manifest
3. Commit the change to Git with message like: `Update image tag to 1.0.1`
4. Push to main branch (or configured branch)
5. Flux reconciles and deploys the new image

#### Controlling Update Behavior

**Suspend Automation Temporarily**:
```bash
flux suspend image update flux-system
# Make manual changes
flux resume image update flux-system
```

**Pin Specific Version** (remove policy marker):
```yaml
image:
  tag: 1.2.3  # Pinned - no policy marker
```

**Change Update Branch**:
```yaml
# In ImageUpdateAutomation resource
spec:
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        name: fluxcdbot
        email: flux@example.com
    push:
      branch: auto-updates  # Push to different branch for PR workflow
```

#### Best Practices
- **Use semver policies** for production workloads to avoid breaking changes
- **Test in dev environment** before enabling auto-updates in production
- **Monitor update commits** in Git history for unexpected changes
- **Set up Flux notifications** for failed image updates
- **Document policy decisions** in ImagePolicy annotations

#### Troubleshooting Image Updates

**Issue: Images not updating**
1. Check ImageRepository status: `kubectl get imagerepositories -A`
2. Check ImagePolicy status: `kubectl get imagepolicies -A`
3. Check ImageUpdateAutomation status: `kubectl get imageupdateautomations -A`
4. Verify policy marker syntax in manifest
5. Check image-automation-controller logs: `kubectl logs -n flux-system deploy/image-automation-controller`

**Issue: Wrong image version selected**
1. Review ImagePolicy rules (semver range, regex pattern)
2. Check available tags: `kubectl get imagerepository <name> -o yaml | yq '.status.lastScanResult'`
3. Adjust policy constraints as needed

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

> **Tip**: Use `#file:manage-secrets.prompt.md` for guided secret creation

#### Sealed Secrets Key Backup and Recovery

**CRITICAL**: The sealed-secrets private key is required to decrypt all SealedSecret resources. Loss of this key means permanent loss of all encrypted secrets.

**Backup Procedure** (Quarterly Recommended):
```bash
# Export sealed-secrets keys (TLS cert and key)
kubectl get secret -n sealed-secrets-system sealed-secrets-key -o yaml > sealed-secrets-backup.yaml

# Store securely (encrypted, off-cluster location)
# Options: password manager, encrypted USB drive, secure cloud storage
```

**Recovery Procedure** (Disaster Recovery):
```bash
# Restore sealed-secrets key in new cluster
kubectl apply -f sealed-secrets-backup.yaml

# Restart sealed-secrets controller to load key
kubectl rollout restart deployment -n sealed-secrets-system sealed-secrets-controller

# Verify unsealing works
kubectl get sealedsecrets -A
kubectl get secrets -A | grep sealed
```

**Key Rotation** (Annual Recommended):
```bash
# Generate new key pair
kubectl create secret tls sealed-secrets-new-key \
  --cert=new-cert.pem \
  --key=new-key.pem \
  -n sealed-secrets-system

# Sealed-secrets controller automatically picks up new key
# Old key remains for decrypting existing secrets
# Re-seal all secrets with new key over time
```

**Public Key Location**: `etc/certs/pub-sealed-secrets.pem` (safe to commit to Git)

**Security Considerations**:
- **NEVER** commit unsealed secrets or the private key to Git
- **Store backups encrypted** with strong encryption (GPG, age, etc.)
- **Test recovery procedure** annually to ensure backups are valid
- **Document key custodians** who have access to backups
- **Use separate keys per cluster** in multi-cluster environments

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

> **Guided workflow**: `#file:manage-secrets.prompt.md create secret`

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

#### Failed HelmRelease Recovery Procedures

When HelmReleases fail, follow this systematic recovery process:

**Step 1: Identify Failure Cause**
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

**Step 2: Common Failure Patterns and Solutions**

| Failure Type | Symptoms | Resolution Steps |
|--------------|----------|------------------|
| **Timeout** | `Install/Upgrade timeout` | 1. Increase `spec.timeout` in HelmRelease<br>2. Check pod startup logs<br>3. Verify resource availability<br>4. Check init containers |
| **Values Error** | `Values validation failed` | 1. Validate values structure: `helm template <chart> -f values.yaml`<br>2. Check valuesFrom references exist<br>3. Compare with chart schema<br>4. Fix values and commit |
| **Chart Not Found** | `Chart not found` | 1. Verify HelmRepository is Ready<br>2. Check chart name spelling<br>3. Verify chart version exists<br>4. Update HelmRepository: `flux reconcile source helm <repo>` |
| **CRD Missing** | `CRD not found` | 1. Identify required CRDs<br>2. Install CRDs first via separate HelmRelease<br>3. Add `dependsOn` to main HelmRelease<br>4. Use `spec.install.crds: CreateReplace` |
| **Dependency Not Ready** | `Dependency not ready` | 1. Check dependency status<br>2. Fix dependency first<br>3. Wait for Ready condition<br>4. Flux will auto-retry |
| **Image Pull Error** | Pods in `ImagePullBackOff` | 1. Verify image exists in registry<br>2. Check image pull secrets<br>3. Test registry access from cluster<br>4. Verify image tag |

**Step 3: Force Remediation**

**Option A: Reconcile HelmRelease**
```bash
# Force immediate reconciliation
flux reconcile helmrelease <name> -n <namespace>

# Watch status
watch kubectl get hr <name> -n <namespace>
```

**Option B: Suspend and Resume** (for persistent failures)
```bash
# Suspend to prevent retry loops
flux suspend helmrelease <name> -n <namespace>

# Fix underlying issue (update values, fix dependencies, etc.)
# Commit changes to Git

# Resume after fix
flux resume helmrelease <name> -n <namespace>
```

**Option C: Manual Rollback**
```bash
# View Helm release history
helm history <name> -n <namespace>

# Rollback to previous working version
helm rollback <name> <revision> -n <namespace>

# Update HelmRelease in Git to prevent re-upgrade
```

**Option D: Delete and Recreate** (last resort)
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

**Step 4: Persistent MongoDB Failures (LibreChat Example)**

The `ai/librechat` HelmRelease historically fails with MongoDB container verification errors:

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

**Step 5: Validation After Recovery**
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

**Step 6: Prevention**

- **Set appropriate timeouts**: Base on historical deployment times + 50% buffer
- **Configure retry limits**: `spec.install.remediation.retries: 3`
- **Enable automatic rollback**: `spec.upgrade.remediation.remediateLastFailure: true`
- **Test in dev first**: Deploy to dev namespace before production
- **Pin chart versions**: Avoid `latest` tags
- **Monitor continuously**: Set up alerts for failed HelmReleases

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

> **Quick Help**: Switch to troubleshooter chat mode or use `#file:troubleshoot-flux.prompt.md`

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

### Error Handling and Dependency Chain Management

#### Dependency Chain Overview

The cluster enforces strict dependency ordering:

```
flux-system (GitRepository)
    ↓
┌───────────────────┬─────────────────────┐
│                   │                     │
infra-controllers   monitoring-controllers  capacitor
    ↓                    ↓                     ↓
infra-configs       monitoring-configs    (standalone)
    ↓                    ↓
  apps           (standalone monitoring)
```

#### Dependency Chain Best Practices

**Rule 1: CRDs Before Resources**
- Install operators/controllers (which install CRDs) before resources that use those CRDs
- Example: sealed-secrets controller before SealedSecret resources

**Rule 2: Infrastructure Before Applications**
- Core services (cert-manager, ingress, storage) before apps that use them
- Example: cert-manager before apps with TLS certificates

**Rule 3: Secrets Before Consumers**
- Ensure SealedSecrets are created and unsealed before apps reference them
- Use `dependsOn` to enforce ordering

**Rule 4: Parallel When Possible**
- Independent resources can deploy in parallel
- Example: monitoring-controllers and infra-controllers are independent

#### Troubleshooting Dependency Issues

**Symptom: "Dependency not ready" error**

1. **Identify the dependency chain**:
```bash
# Check Kustomization dependencies
kubectl get kustomization -n flux-system -o yaml | yq '.items[] | {"name": .metadata.name, "dependsOn": .spec.dependsOn}'

# Visualize status
flux get kustomizations -A
```

2. **Check dependency status**:
```bash
# Get detailed status of blocking dependency
kubectl describe kustomization <dependency-name> -n flux-system

# Check resources in dependency
kubectl get all -n <dependency-namespace>
```

3. **Common dependency failure causes**:

| Cause | Detection | Resolution |
|-------|-----------|------------|
| **CRDs not installed** | `no matches for kind` errors | Install CRD-providing operator first |
| **Namespace missing** | `namespace not found` | Create namespace in dependency Kustomization |
| **Resource conflict** | `resource already exists` | Remove conflicting resource or change name |
| **Health check timeout** | Dependency shows `Progressing` | Increase timeout or fix unhealthy resources |
| **Circular dependency** | Both resources waiting | Remove circular `dependsOn`, redesign |

4. **Force dependency reconciliation**:
```bash
# Reconcile dependency first
flux reconcile kustomization <dependency-name>

# Wait for Ready status
watch kubectl get kustomization <dependency-name> -n flux-system

# Then reconcile dependent
flux reconcile kustomization <dependent-name>
```

#### Error Recovery Strategies

**Strategy 1: Cascading Reconciliation** (for dependency chain failures)
```bash
# Reconcile from root to leaf
flux reconcile source git flux-system
flux reconcile kustomization infra-controllers
flux reconcile kustomization infra-configs
flux reconcile kustomization apps
```

**Strategy 2: Suspend and Debug** (for persistent issues)
```bash
# Suspend auto-reconciliation
flux suspend kustomization apps

# Debug and fix issues
# Test fixes locally: kustomize build apps/kyrion/

# Resume when ready
flux resume kustomization apps
```

**Strategy 3: Partial Deployment** (for isolating failures)
```bash
# Temporarily remove failing app from kustomization
# Edit apps/kyrion/kustomization.yaml, comment out failing resource
# Commit and push

# Fix failing app separately
# Uncomment and redeploy when fixed
```

**Strategy 4: Fresh Start** (for corrupted state)
```bash
# Delete Kustomization (keeps deployed resources)
kubectl delete kustomization <name> -n flux-system

# Reconcile parent to recreate
flux reconcile kustomization flux-system
```

#### Health Check Configuration

Configure appropriate health checks to prevent false positives:

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: apps
  namespace: flux-system
spec:
  # Wait up to 10 minutes for resources to be ready
  timeout: 10m
  
  # Check every 30 seconds during reconciliation
  interval: 5m
  
  # Retry failed reconciliation after 2 minutes
  retryInterval: 2m
  
  # Health check configuration
  wait: true  # Wait for resources to be ready
  
  # Specific health checks for resources
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: critical-app
      namespace: production
```

#### Monitoring Flux Health

**Real-time Monitoring**:
```bash
# Watch all Kustomizations
watch -n 5 'flux get kustomizations -A'

# Watch all HelmReleases
watch -n 5 'kubectl get hr -A'

# Monitor Flux events
kubectl get events -n flux-system --watch
```

**Alerts and Notifications**:
- Configure Flux Alert resources for Slack/Discord/email notifications
- Monitor Prometheus metrics: `gotk_reconcile_condition`
- Set up Grafana dashboards for Flux controller metrics

**Automated Recovery**:
- Flux automatically retries failed reconciliations per `retryInterval`
- Configure `remediation` strategies in HelmReleases for automatic rollback
- Use `prune: true` to clean up orphaned resources

### Critical File References
- **Flux entry point**: `clusters/kyrion/apps.yaml`
- **App definitions**: `apps/kyrion/kustomization.yaml` 
- **Infrastructure config**: `infrastructure/configs/kustomization.yaml`
- **Cluster secrets**: `clusters/kyrion/sealed-secrets.yaml`
- **Image policies**: Search for `imageupdateautomation.yaml`

### HelmRepository Inventory

The cluster uses 18 HelmRepository sources for chart distribution:

| Repository | Type | URL/OCI Path | Charts Used | Notes |
|------------|------|--------------|-------------|-------|
| **onechart** | Standard | https://chart.onechart.dev | Most applications | Primary chart repository for apps |
| **bitnami** | OCI | oci://registry-1.docker.io/bitnamicharts | MongoDB, PostgreSQL, Redis | Bitnami application charts |
| **sealed-secrets** | Standard | https://bitnami-labs.github.io/sealed-secrets | sealed-secrets | Secret encryption |
| **cert-manager** | Standard | https://charts.jetstack.io | cert-manager | Certificate management |
| **traefik** | Standard | https://traefik.github.io/charts | traefik | Ingress controller |
| **tailscale** | Standard | https://pkgs.tailscale.com/helmcharts | tailscale-operator | Private networking |
| **kube-prometheus-stack** | OCI | oci://ghcr.io/prometheus-community/charts | kube-prometheus-stack | Monitoring stack |
| **grafana-charts** | Standard | https://grafana.github.io/helm-charts | loki, tempo, promtail | Log and trace backends |
| **elastic** | Standard | https://helm.elastic.co | elasticsearch, kibana | Log indexing |
| **coder-v2** | Standard | https://helm.coder.com/v2 | coder | Development workspaces |
| **fission-charts** | Standard | https://fission.github.io/fission-charts | fission-all | Serverless functions |
| **gha-runner-scale-set** | OCI | oci://ghcr.io/actions/actions-runner-controller-charts | gha-runner-scale-set | ARC runner sets |
| **capacitor** | OCI | oci://ghcr.io/gimlet-io/capacitor | capacitor | Image update dashboard |
| **intel** | Standard | https://intel.github.io/helm-charts | intel-device-plugins-operator | GPU device plugin |
| **rancher-charts** | Standard | https://releases.rancher.com/server-charts/latest | system-upgrade-controller | K3s upgrades |
| **go-skynet** | Standard | https://go-skynet.github.io/helm-charts | local-ai | Local AI inference |
| **open-webui** | Standard | https://helm.openwebui.com | open-webui | LLM web interface |
| **otwld** | Standard | https://otwld.github.io/ollama-helm | ollama | Ollama LLM server |

**Update Intervals**:
- Most repositories: 1h (balance between freshness and load)
- Critical infrastructure: 24h (cert-manager, sealed-secrets)
- Development tools: 30m (coder, fission)

**Adding New HelmRepositories**:

**Standard Repository**:
```yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: HelmRepository
metadata:
  name: my-charts
  namespace: flux-system
spec:
  url: https://charts.example.com
  interval: 1h
  timeout: 1m
```

**OCI Repository**:
```yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: HelmRepository
metadata:
  name: my-oci-charts
  namespace: flux-system
spec:
  type: oci
  url: oci://registry.example.com/charts
  interval: 1h
```

**Private Repository** (with authentication):
```yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: HelmRepository
metadata:
  name: private-charts
  namespace: flux-system
spec:
  url: https://private-charts.example.com
  interval: 1h
  secretRef:
    name: helm-repo-secret  # Secret with username/password
```

**Troubleshooting HelmRepositories**:
```bash
# Check repository status
flux get sources helm -A

# Verify repository is accessible
kubectl describe helmrepository <name> -n flux-system

# Force repository update
flux reconcile source helm <name>

# Check source-controller logs
kubectl logs -n flux-system deploy/source-controller | grep HelmRepository/<name>
```

**Common Issues**:
- **Repository timeout**: Increase `spec.timeout` or check network access
- **Authentication failed**: Verify credentials in `secretRef`
- **Chart not found**: Verify chart name and version exist in repository index
- **OCI registry errors**: Verify OCI URL format and registry authentication

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
4. **Version Control**: All changes tracked via Git commits following [Conventional Commits](https://www.conventionalcommits.org/)
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

### Web-Based Troubleshooting Workflow

The cluster supports **complete troubleshooting and resolution through GitHub web interface** - no local IDE or Codespaces required.

#### Overview

```
GitHub Issue → Copilot Diagnostics → Root Cause Analysis → Approval → Coding Agent → Fix → Validation
```

**Key Components**:
- **GitHub Issues**: Structured templates for bug reports and troubleshooting requests
- **GitHub Copilot Chat**: AI-powered diagnostics in browser
- **Copilot Agents**: Specialized agents for investigation, coordination, and knowledge base
- **Coding Agent**: Automated PR creation for fixes
- **Circuit Breaker**: Protection against infinite retry loops (3 attempts max)
- **Knowledge Base**: Searchable history of past issues and resolutions

#### Quick Start

1. **Create Issue**: https://github.com/alecsg77/elysium/issues/new/choose
   - Select template: 🔍 Troubleshooting Request or 🐛 Bug Report
   - Fill out structured form with symptoms and context

2. **Invoke Copilot**: Choose your method:
   
  **Agent Session (Full Automation)**:
  - Click "Agent session" on issue page
  - Select `troubleshooter` agent
  - Prompt: `Please investigate this issue https://github.com/alecsg77/elysium/issues/[N] and run diagnostics`
  - ✅ Can create PR automatically
   
  **Copilot Chat (Advisory)**:
  - Open Copilot Chat on issue page
  - Prompt: `@alecsg77/elysium/files/.github/agents/troubleshooter.agents.md Please investigate this issue and run diagnostics`
  - ✅ Provides detailed analysis and recommendations

3. **Review Analysis**: Copilot posts diagnostic reports in phases:
   - Health Check → Resource Status → Logs → Events → Configuration → Root Causes

4. **Approve Resolution**: After plans generated, approve with:
   ```
   /approve-plan
   ```

5. **Monitor Progress**: Coding agent creates PR, coordinator validates deployment

#### Agents

**Agents are flexible and adapt to available tools**:
- In VS Code/Codespaces: Can run kubectl, flux, and Git commands directly
- In GitHub Web UI: Provides commands for user to run and paste results
- All environments: Uses GitHub Issues for tracking and coordination

**Troubleshooter** (`.github/agents/troubleshooter.agents.md`):
- Searches knowledge base for known fixes
- Runs comprehensive diagnostics (adapts to available tools)
- Identifies distinct root causes vs symptoms
- Creates child bug issues per root cause
- Posts phase-based diagnostic reports

**Issue Coordinator** (`.github/agents/issue-coordinator.agents.md`):
- Generates GitOps-compliant resolution plans
- Manages approval workflow
- Submits token-optimized requests to coding agent
- Validates deployments via Flux reconciliation
- Implements circuit breaker (3 attempts → manual intervention)

**Knowledge Base** (`.github/agents/knowledge-base.agents.md`):
- Searches closed issues for similar problems
- Extracts resolution patterns
- Suggests known fixes with confidence scores
- Accelerates troubleshooting for repeat issues

#### Workflow Phases

**Phase 1: Issue Creation**
- Use structured templates capturing component, severity, symptoms, errors
- Include recent changes and attempted fixes
- Link to related issues if known

**Phase 2: Knowledge Base Search**
- Automatic search for similar past issues
- If high-confidence match found (>80%), suggest known fix immediately
- If no match, proceed to full diagnostics

**Phase 3: Diagnostics**
- Agent adapts to available tools (direct kubectl access vs guided user commands)
- Collects Flux status, resource conditions, logs, events, configurations
- Posts results as sequential comments (50k char limit per comment)
- Uses collapsible sections for verbose output

**Phase 4: Root Cause Analysis**
- Analyzes diagnostic data to identify distinct root causes
- Separates causes from symptoms and cascading failures
- Creates one child bug issue per independent root cause
- Updates parent issue with task list linking children

**Phase 5: Resolution Planning**
- Generates GitOps-compliant plans for each child issue
- Specifies exact file changes, validation steps, rollback procedures
- Posts consolidated review comment on parent issue
- Awaits `/approve-plan` command

**Phase 6: Implementation**
- Submits token-optimized requests to coding agent
- Coding agent creates PR with conventional commit messages
- Tracks resolution attempts with labels (`resolution-attempt:1`, `resolution-attempt:2`, etc.)

**Phase 7: Validation**
- After PR merge, coordinator monitors Flux reconciliation (10-minute window)
- Checks Kustomization/HelmRelease status, pod health, events
- **Success**: Closes issue, triggers knowledge base update
- **Failure**: Generates new plan (if < 3 attempts) or triggers circuit breaker

#### Circuit Breaker System

Prevents infinite retry loops:

| Attempts | Status | Action |
|----------|--------|--------|
| 1 | First try | Submit to coding agent |
| 2 | Retry | Adjust plan based on first failure |
| 3 | Final attempt | Last automated try |
| 3+ | **Circuit breaker triggered** | Manual intervention required, label: `circuit-breaker:triggered` |

**Reset circuit breaker** after manual fix:
```
/reset-attempts
Manually fixed [underlying issue]. Ready to retry.
```

#### Approval Commands

| Command | Effect |
|---------|--------|
| `/approve-plan` | Approve all resolution plans in review |
| `/reject` | Reject plans, request alternative approach |
| `/reset-attempts` | Reset circuit breaker after manual intervention |
| Comment with feedback | Request specific changes to plans |

#### Token Optimization

Coding agent requests are optimized for token efficiency:
- **Inline critical context**: Full error message + stack trace (max 2000 chars)
- **Reference full details**: Link to diagnostic reports for complete context
- **Semantic completeness**: Include essential meaning, remove verbosity
- **Target**: 1500-2000 tokens per request for best results

#### Knowledge Base

**Automatic Updates**:
1. Issue closed with `status:resolved` label
2. Workflow extracts root cause, resolution, and learnings
3. PR created updating `.github/KNOWN_ISSUES.md`
4. Auto-merged after validation
5. Future searches benefit from documented pattern

**Manual Search**:
```bash
# By component
grep -A 20 "## Component: Flux CD" .github/KNOWN_ISSUES.md

# By error message
grep -i "error pattern" .github/KNOWN_ISSUES.md
```

#### Example Workflow

```markdown
1. User creates troubleshooting request: "LibreChat pods crashing"
2. Knowledge base search finds similar MongoDB issue (#123)
3. Suggests known fix: Delete and recreate PVC
4. User tries fix → doesn't work (different root cause)
5. Copilot runs full diagnostics
6. Identifies root cause: Missing API key in sealed secret
7. Creates child bug issue with details
8. Generates resolution plan: Add sealed secret key
9. User approves: /approve-plan
10. Coding agent creates PR with fix
11. PR merged → Flux reconciles
12. Coordinator validates: Pods Running
13. Issue closed → Knowledge base updated
```

#### Best Practices

**Reporting Issues**:
- ✅ Provide exact error messages
- ✅ Note when problem started
- ✅ List recent changes
- ✅ Include attempted fixes
- ❌ Don't be vague ("it's broken")
- ❌ Don't report multiple unrelated issues in one

**During Investigation**:
- ✅ Review diagnostic reports carefully
- ✅ Check if similar issues exist
- ✅ Be patient (diagnostics take 2-5 minutes)
- ❌ Don't make manual changes during investigation
- ❌ Don't submit duplicate requests

**Approving Plans**:
- ✅ Read resolution plans completely
- ✅ Verify changes match root cause
- ✅ Consider impact and timing
- ✅ Ask questions if unsure
- ❌ Don't auto-approve without review
- ❌ Don't approve changes you don't understand

#### Troubleshooting Resources

- **User Guide**: `.github/TROUBLESHOOTING.md` - Complete workflow examples
- **Known Issues**: `.github/KNOWN_ISSUES.md` - Past resolutions by component
- **Root Cause Analysis**: `.github/prompts/analyze-root-cause.prompt.md` - Analysis methodology
- **Resolution Requests**: `.github/prompts/request-resolution.prompt.md` - Token optimization guide
- **Issue Templates**: `.github/ISSUE_TEMPLATE/` - Structured reporting forms

### Support and Resources

#### Quick Help
- **Deploy app**: `#file:deploy-app.prompt.md`
- **Debug issue**: Switch to troubleshooter chat mode
- **Review config**: `#file:review-config.prompt.md`
- **Manage secrets**: `#file:manage-secrets.prompt.md`
- **Generate docs**: `#file:generate-docs.prompt.md`

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
