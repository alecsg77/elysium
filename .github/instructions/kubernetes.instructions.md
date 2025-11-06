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
