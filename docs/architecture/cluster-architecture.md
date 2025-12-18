# Cluster Architecture

Complete architectural documentation for the Elysium Kubernetes homelab cluster.

## Overview

This is a **GitOps-driven Kubernetes homelab** using Flux CD for declarative cluster management. The repository structure follows a layered approach with strict dependency ordering.

## Network Architecture

### Network Topology
- **Private Network**: Kubernetes cluster is deployed in a private network with internet access
- **Not Cloud-Accessible**: Cluster is not reachable from GitHub-hosted runners or public internet
- **Self-Hosted Runners**: GitHub Copilot agent runs on self-hosted runners inside the cluster using ARC (Actions Runner Controller)
- **Cluster Access**: Copilot agent has direct access to the Kubernetes API server from within the cluster network

### Network Integration Components

#### Tailscale Mesh
Private overlay network for secure cluster access:
- Ingress class: `tailscale`
- Domain suffix: `*.ts.net`
- DNS configuration via `ts-dns` resource
- Default proxy class: `ts-default-proxy-class`

#### Traefik Ingress
HTTP/HTTPS routing and TLS termination:
- IngressRoute resources for HTTP routing
- TLSOption resources for TLS configuration
- cert-manager integration for automatic certificate provisioning
- Traefik Hub features enabled

#### Azure Arc Integration (Optional)
Hybrid cloud management:
- Namespaces: `azure-arc`, `azure-arc-release`
- Arc Workload Identity for Azure service authentication
- Namespace: `arc-workload-identity`
- Monitoring integration via `arc-workload-identity-monitor`

#### Actions Runner Controller (ARC)
GitHub Actions self-hosted runners:
- Namespaces: `arc-runners`, `arc-system`
- Runner sets: `coder`, `copilot`, `fission`, `raiplaysoundrss`
- Scales runners based on GitHub Actions job demand
- Kubernetes-native runner lifecycle management

## Technology Stack

### Core Components
- **GitOps**: Flux CD v2 with image automation
- **Orchestration**: Kubernetes (K3s)
- **Package Management**: Helm 3 + Kustomize
- **Secrets**: Bitnami Sealed Secrets
- **Ingress**: Traefik with cert-manager
- **Networking**: Tailscale for private access

### Observability Stack
- **Metrics**: Prometheus, Grafana, Alertmanager
- **Logging**: Loki, Promtail, Elasticsearch
- **Tracing**: Tempo, Jaeger, OpenTelemetry
- **Storage**: Minio (S3-compatible for Loki/Tempo blocks)

### Storage
- **Local Storage**: Local path provisioner
- **Cloud Storage**: rclone CSI for cloud provider integration

### CI/CD
- **Runners**: Actions Runner Controller (ARC) for self-hosted GitHub Actions runners
- **Functions**: Fission framework for serverless functions

## Namespace Organization

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

### Namespace Conventions
- **System namespaces**: Reserved by Kubernetes
- **Infrastructure**: Cluster-wide services with elevated privileges
- **Application**: Isolated workloads with specific RBAC
- **Monitoring**: Read-only access to cluster metrics and logs

## Monitoring Architecture

### Data Flow
```
Applications/Pods
    ↓ metrics
Prometheus (scrape) → Grafana (visualize) → Alertmanager (alert)
    ↓ logs
Promtail → Loki → Grafana
    ↓ logs (indexed)
Promtail → Elasticsearch → Jaeger
    ↓ traces
OpenTelemetry Collector → Tempo → Grafana
                        → Jaeger → Grafana
```

### Components

#### Metrics (kube-prometheus-stack)
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert routing and notifications
- Location: `monitoring/controllers/kube-prometheus-stack/`

#### Logging (loki-stack)
- **Loki**: Log aggregation and storage
- **Promtail**: Log collection agent
- Location: `monitoring/controllers/loki-stack/`

#### Tracing (tempo-stack)
- **Tempo**: Distributed tracing backend
- **OpenTelemetry**: Trace collection and processing
- **Jaeger**: Trace UI and query service
- Location: `monitoring/controllers/tempo-stack/`, `monitoring/controllers/opentelemetry/`

#### Log Indexing (elastic)
- **Elasticsearch**: Full-text log indexing for Jaeger
- Location: `monitoring/controllers/elastic/`

#### Proxy (pushprox)
- **PushProx**: Prometheus proxy for metrics behind firewalls
- Location: `monitoring/controllers/pushprox/`

### Storage Backend
- **Minio**: S3-compatible object storage for Loki and Tempo blocks
- Provides long-term storage for logs and traces

## AI/ML Workload Stack

The cluster hosts comprehensive AI/ML infrastructure in the `ai` namespace:

| Application | Purpose | Key Features |
|------------|---------|-------------|
| **Ollama** | LLM inference server | Local model hosting, GPU acceleration |
| **Open WebUI** | Web interface for LLMs | Chat interface, prompt management |
| **LibreChat** | Multi-model chat platform | OpenAI-compatible API, conversation management |
| **LocalAI** | OpenAI-compatible API | Local model inference, multiple backends |
| **SearXNG** | Privacy-focused metasearch | AI context gathering, web search integration |

### Hardware Acceleration
AI workloads utilize Intel GPU resources (`gpu.intel.com/i915`) for inference acceleration.

### Common Issues
- **LibreChat MongoDB**: Historically fails with container verification errors - check MongoDB pod logs and persistent volume integrity
- **GPU allocation**: Ensure Intel GPU device plugin is running and devices are available
- **Model downloads**: Large models may cause slow startup - check init container logs

## Flux CD Architecture

### Components

The cluster uses Flux CD v2 with **image-reflector-controller** and **image-automation-controller** for automated image updates:

| Controller | Purpose | Key Features |
|------------|---------|--------------|
| **Source Controller** | Manages sources | Git, OCI, Bucket, Helm repositories |
| **Kustomize Controller** | Applies manifests | Dependency management, health checks, pruning |
| **Helm Controller** | Manages releases | Values injection, lifecycle hooks, rollbacks |
| **Image Reflector** | Scans registries | Image tag discovery, policy evaluation |
| **Image Automation** | Updates Git | Automated commits for image updates |
| **Notification Controller** | Alerting | Webhooks, events, receivers |

### Custom Resource Definitions (CRDs)

#### Source Controller CRDs
- **GitRepository**: Points to Git repositories containing Kubernetes manifests or Helm charts
- **OCIRepository**: References OCI artifacts (container registry stored manifests/charts)
- **Bucket**: S3-compatible storage sources
- **HelmRepository**: Helm chart repositories
- **HelmChart**: Individual chart references from repositories

#### Kustomize Controller CRDs
- **Kustomization**: Builds and applies Kubernetes manifests from sources with dependency management

#### Helm Controller CRDs
- **HelmRelease**: Manages Helm chart deployments with values injection and lifecycle management

#### Image Automation CRDs
- **ImageRepository**: Scans container registries for available image tags
- **ImagePolicy**: Defines rules for selecting latest/suitable image versions
- **ImageUpdateAutomation**: Automatically updates Git repository with new image references

#### Notification Controller CRDs
- **Provider**: Notification destinations (Slack, Discord, webhooks)
- **Alert**: Event filtering and forwarding rules
- **Receiver**: Webhook endpoints for triggering reconciliation

### Dependency Chain

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

## HelmRepository Inventory

The cluster uses 18 HelmRepository sources for chart distribution:

| Repository | Type | URL/OCI Path | Charts Used | Notes |
|------------|------|--------------|-------------|-------|
| **onechart** | Standard | https://chart.onechart.dev | Legacy apps, generic deployments | Generic chart wrapper (use only when no official chart exists) |
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

### Update Intervals
- **Most repositories**: 1h (balance between freshness and load)
- **Critical infrastructure**: 24h (cert-manager, sealed-secrets)
- **Development tools**: 30m (coder, fission)

## Repository Structure

### Directory Layout

```
clusters/kyrion/          # Cluster bootstrap (Flux entry point)
├── apps.yaml            # Applications Kustomization
├── infrastructure.yaml  # Infrastructure Kustomization
├── monitoring.yaml      # Monitoring Kustomization
├── sealed-secrets.yaml  # Cluster-wide secrets
└── flux-system/         # Flux bootstrap

apps/                    # Application deployments
├── base/               # Shared app configurations
└── kyrion/            # Environment-specific overlays

infrastructure/          # Core infrastructure
├── controllers/        # Operators and CRDs
└── configs/           # Cluster-wide configs

monitoring/             # Observability stack
├── controllers/       # Monitoring operators
└── configs/          # Dashboards and datasources

coder/                 # Development templates
├── templates/        # Coder workspace templates

functions/            # Serverless functions
└── specs/           # Fission function specs
```

**Authoritative Reference**: [Repository Structure Standards](/docs/standards/repository-structure.md)

## External Dependencies

### Storage
- **Media Library**: Azure Blob Storage via rclone CSI
  - Mount path: `/mnt/media-library`
  - Automount may take 2-5 minutes on pod start
  - Apps using external storage should have init containers with mount detection
  - Example: Apps in `arkham` namespace wait for mount before starting

### Network
- **Tailscale**: Private network overlay for secure access
  - Ingress class: `tailscale`
  - Domain: `*.ts.net`
  - Apps with `ts-ingress.yaml` accessible privately

### Image Registries
- **Docker Hub**: Public images (rate-limited)
- **GitHub Container Registry**: Private images (authenticated)
- **Custom Registry**: `arkham.docker.local` for local builds

## Security Model

### Secrets Management
- **Sealed Secrets**: All sensitive data encrypted using Bitnami Sealed Secrets
- **Public Key**: `etc/certs/pub-sealed-secrets.pem` (safe to commit)
- **Private Key**: Stored only in cluster (never committed to Git)
- See [Secret Management Guide](/docs/security/secret-management.md) for details

### RBAC Strategy
- **Namespace isolation**: Each application namespace has dedicated ServiceAccounts
- **Least privilege**: Controllers granted only required permissions
- **Cluster-admin**: Reserved for infrastructure components only

### Network Policies
- **Default deny**: Namespaces have default deny policies where applicable
- **Explicit allow**: Only required communication paths allowed
- **Monitoring exemption**: Prometheus/Grafana have read-only cluster access

## Operational Patterns

### GitOps Workflow
1. **Change proposal**: Create PR with manifest changes
2. **Review**: Validate changes against standards
3. **Merge**: Changes committed to main branch
4. **Sync**: Flux detects changes (1h interval or manual reconcile)
5. **Apply**: Flux applies changes to cluster
6. **Validate**: Monitor deployment status and health

### Dependency Management
- **Infrastructure first**: Controllers and CRDs installed before configs
- **Configs before apps**: Cluster policies applied before workloads
- **Explicit ordering**: Use `spec.dependsOn` in Kustomizations
- **Health checks**: Wait for resources to be ready before continuing

### Resource Lifecycle
- **Creation**: Defined in Git → Applied by Flux → Created in cluster
- **Updates**: Change in Git → Flux detects → Updates cluster
- **Deletion**: Remove from Git → Flux prunes → Deleted from cluster
- **Drift detection**: Flux reconciles cluster state to match Git

## Disaster Recovery

### Backup Strategy
- **Git repository**: Primary backup (entire cluster state)
- **Sealed secrets key**: Quarterly backup to secure location
- **Persistent volumes**: Application-specific backup procedures
- **Monitoring data**: Long-term storage in Minio (Loki/Tempo blocks)

### Recovery Procedure
1. **Bootstrap Flux**: Run `scripts/bootstrap_flux.sh` on new cluster
2. **Restore sealed-secrets key**: Apply backup to enable secret decryption
3. **Wait for reconciliation**: Flux rebuilds entire cluster state from Git
4. **Restore PVs**: Restore application data from backups if needed
5. **Validate**: Check all applications are running and healthy

### Key Recovery Points
- **Flux bootstrap**: Restores all controllers and infrastructure
- **Sealed secrets**: Required for decrypting all secrets
- **Git repository**: Must be accessible for recovery
- **External storage**: rclone mounts require cloud credentials

## Performance Characteristics

### Resource Requirements
- **Control plane**: K3s requires minimal resources (512Mi RAM, 1 CPU)
- **Flux controllers**: ~200Mi RAM total for all controllers
- **Monitoring stack**: ~2Gi RAM (Prometheus, Grafana, Loki)
- **Applications**: Varies by workload

### Scaling Considerations
- **Horizontal**: Add nodes for capacity
- **Vertical**: Increase node resources for demanding workloads
- **Storage**: Local storage scales with node disk capacity
- **Network**: Tailscale mesh scales to hundreds of nodes

## References

- **Repository Standards**: [Repository Structure](/docs/standards/repository-structure.md)
- **Troubleshooting**: [Known Issues](/docs/troubleshooting/known-issues.md)
- **Runbooks**: [Application Deployment](/docs/runbooks/add-application.md)
- **Security**: [Secret Management](/docs/security/README.md)
