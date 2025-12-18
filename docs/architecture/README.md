# Architecture

Comprehensive documentation about the Elysium Kubernetes homelab cluster architecture.

## Contents

- **[Cluster Architecture](cluster-architecture.md)** - Complete architectural documentation including:
  - Network architecture (Tailscale, Traefik, Azure Arc, ARC runners)
  - Technology stack (GitOps, monitoring, storage, CI/CD)
  - Namespace organization (25+ namespaces)
  - Monitoring architecture (Prometheus, Grafana, Loki, Tempo, Jaeger, OpenTelemetry)
  - AI/ML workload stack (Ollama, Open WebUI, LibreChat, LocalAI, SearXNG)
  - Flux CD architecture (controllers, CRDs, dependency chain)
  - HelmRepository inventory (18 chart repositories)
  - External dependencies (storage, network, registries)
  - Security model and RBAC strategy
  - Disaster recovery procedures

## Quick Links

### Network
- **Private Network**: Cluster not cloud-accessible, uses self-hosted runners
- **Tailscale**: `*.ts.net` domain for private ingress
- **Traefik**: HTTP/HTTPS routing with cert-manager TLS
- **Azure Arc**: Optional hybrid cloud management

### Monitoring
- **Metrics**: Prometheus → Grafana → Alertmanager
- **Logs**: Promtail → Loki/Elasticsearch → Grafana/Jaeger
- **Traces**: OpenTelemetry → Tempo/Jaeger → Grafana

### GitOps
- **Flux CD v2**: Continuous reconciliation from Git
- **Dependency Chain**: infra-controllers → infra-configs → apps
- **Image Automation**: Automatic image tag updates

## Related Documentation

- [Repository Structure Standards](/docs/standards/repository-structure.md)
- [Application Deployment](/docs/runbooks/add-application.md)
- [HelmRelease Recovery](/docs/runbooks/helm-release-recovery.md)
- [Known Issues](/docs/troubleshooting/known-issues.md)

