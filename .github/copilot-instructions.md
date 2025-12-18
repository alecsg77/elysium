# Elysium: GitOps-Managed Kubernetes Homelab

This document provides essential context for GitHub Copilot when working with the Elysium Kubernetes homelab cluster.

**For detailed documentation, see**: [/docs/README.md](/docs/README.md)

## Quick Reference

| Need | Reference |
|------|-----------|
| **Architecture details** | [Cluster Architecture](/docs/architecture/cluster-architecture.md) |
| **Repository standards** | [Repository Structure](/docs/standards/repository-structure.md) |
| **Deploy application** | [Application Deployment Runbook](/docs/runbooks/add-application.md) |
| **Fix HelmRelease** | [HelmRelease Recovery](/docs/runbooks/helm-release-recovery.md) |
| **Manage secrets** | [Secret Management Guide](/docs/security/secret-management.md) |
| **Troubleshoot issue** | [Known Issues](/docs/troubleshooting/known-issues.md) |

## Essential Context

### Cluster Overview

- **Type**: GitOps-driven Kubernetes homelab using Flux CD
- **Network**: Private network, not cloud-accessible
- **Access**: Self-hosted runners inside cluster (ARC)
- **Repository**: Monorepo with strict dependency ordering

See [Cluster Architecture](/docs/architecture/cluster-architecture.md) for complete details.

### Repository Structure

**Decision Tree**: [Where should this file go?](/docs/standards/repository-structure.md#where-should-this-file-go-decision-tree)

```
clusters/kyrion/          # Flux bootstrap (entry point)
├── apps.yaml            # Applications Kustomization
├── infrastructure.yaml  # Infrastructure Kustomization
├── monitoring.yaml      # Monitoring Kustomization
└── sealed-secrets.yaml  # Cluster-wide secrets

apps/                    # Applications (base + overlays)
├── base/<app>/         # Environment-agnostic resources
└── kyrion/            # Environment-specific patches

infrastructure/          # Core infrastructure
├── controllers/        # Operators/CRDs (install first)
└── configs/           # Cluster configs (depends on controllers)

monitoring/             # Observability stack
├── controllers/       # Monitoring operators
└── configs/          # Dashboards, datasources

docs/                   # Authoritative documentation
├── architecture/      # Cluster architecture docs
├── standards/         # Repository and code standards
├── runbooks/         # Step-by-step procedures
├── security/         # Security guides
└── troubleshooting/  # Known issues and workflows
```

**Key Principle**: Authoritative documentation lives in `/docs/`, agent guidance in `.github/`.

### Dependency Chain

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

**Rule**: CRDs and operators before resources that use them.

### Technology Stack Quick Reference

| Component | Technology | Location |
|-----------|-----------|----------|
| **GitOps** | Flux CD v2 | `flux-system` namespace |
| **Orchestration** | Kubernetes (K3s) | - |
| **Packages** | Helm 3 + Kustomize | - |
| **Secrets** | Bitnami Sealed Secrets | `sealed-secrets-system` namespace |
| **Ingress** | Traefik + cert-manager | `traefik` namespace |
| **Network** | Tailscale | `tailscale` namespace |
| **Monitoring** | Prometheus, Grafana, Loki, Tempo | `monitoring` namespace |
| **CI/CD** | Actions Runner Controller (ARC) | `arc-system`, `arc-runners` namespaces |

See [Technology Stack](/docs/architecture/cluster-architecture.md#technology-stack) for complete details.

## Key Patterns

### GitOps with Flux CD

**Bootstrap**: `./scripts/bootstrap_flux.sh`

**Reconciliation**:
- **Interval**: 1h automatic, 5m retry on failure
- **Manual**: `flux reconcile source git flux-system`
- **Dependency**: Use `spec.dependsOn` in Kustomizations

**Variable Substitution**:
```yaml
spec:
  postBuild:
    substituteFrom:
      - kind: ConfigMap
        name: cluster-vars
      - kind: Secret
        name: cluster-secret-vars
```

### Application Deployment

**Complete Procedure**: [Application Deployment Runbook](/docs/runbooks/add-application.md)

**Quick Pattern**:
```
1. Create base in apps/base/<app>/
   - namespace.yaml (only if app-specific, not system namespace)
   - helmrelease.yaml or individual resource files
   - kustomization.yaml (NO patches)

2. Create overlay in apps/kyrion/
   - <app>-patch.yaml (patches only)
   - <app>-sealed-secret.yaml (env-specific secrets)
   
3. Validate locally (MANDATORY):
   kustomize build apps/base/<app>/
   kustomize build apps/kyrion/
   flux build kustomization apps --path clusters/kyrion

4. Commit and monitor Flux reconciliation
```

**Base/Overlay Rules**:
- **Base**: Environment-agnostic, no patches, one resource per file
- **Overlay**: Patches only, env-specific resources only

### Helm Chart Selection Priority

1. **Official chart from app owner** (e.g., `coder` from Coder.com)
2. **Official documentation recommendation**
3. **Verified publishers** (Bitnami, Prometheus Community)
4. **Official Kustomize manifests** (use Flux Kustomization)
5. **Generic wrappers** (onechart - last resort only)

See [Chart Selection](/docs/standards/repository-structure.md#chart-selection-priority) for details.

### Secret Management

**⚠️ CRITICAL**: Never commit plain text secrets.

**Create Sealed Secret**:
```bash
echo -n "secret-value" | kubectl create secret generic app-secret \
  --namespace=<namespace> \
  --dry-run=client --from-file=key=/dev/stdin -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > sealed-secret.yaml
```

**Complete Guide**: [Secret Management](/docs/security/secret-management.md)

**For guided workflow**: Use `prompts/manage-secrets.prompt.md`

### Flux Status Detection

**Note**: Some tools may report "No Flux instance found" even when Flux is fully operational.

**Verify Flux is Actually Running**:
```bash
kubectl get pods -n flux-system  # All controllers Running
flux get all -A                  # All resources with status
kubectl get kustomizations -A     # Kustomizations Ready
kubectl get gitrepositories -n flux-system  # Recent commit SHA
```

If these show healthy resources, Flux is working correctly.

See [Flux Status Detection](/docs/architecture/cluster-architecture.md#flux-cd-architecture) for details.

## Development Workflows

### Creating/Modifying Apps

**Complete Procedure**: [Application Deployment Runbook](/docs/runbooks/add-application.md)

**Quick Steps**:
1. Plan: Review repository structure standards
2. Create base: `apps/base/<app>/` with environment-agnostic values
3. Create overlay: `apps/kyrion/` with patches
4. **Validate locally** (mandatory): `kustomize build`, `flux build`
5. Commit with Conventional Commits format
6. Monitor Flux reconciliation

### Managing Secrets

**Quick Reference**: Use guided workflow in `prompts/manage-secrets.prompt.md`

**Commands**:
```bash
# Generic secret
kubectl create secret generic app-secret \
  --namespace=<namespace> --from-literal=key=value \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml > sealed-secret.yaml
```

**Complete Guide**: [Secret Management](/docs/security/secret-management.md)

### Advanced Flux Operations

| Operation | Command |
|-----------|---------|
| **Force sync** | `flux reconcile source git flux-system` |
| **Reconcile app** | `flux reconcile hr <name> -n <namespace>` |
| **Suspend** | `flux suspend kustomization <name>` |
| **Resume** | `flux resume kustomization <name>` |
| **View events** | `flux events --for Kustomization/<name>` |
| **Preview changes** | `flux diff kustomization apps --path clusters/kyrion` |
| **Build locally** | `flux build kustomization apps --path clusters/kyrion` |

### Common Commands

```bash
# Validate YAML
yamllint clusters/ apps/ infrastructure/ monitoring/

# Build Kustomize overlays
kustomize build apps/kyrion/

# Test Helm rendering
helm template <name> <chart> -f values.yaml

# Check Flux health
flux check
flux get all -A

# Monitor resources
watch kubectl get hr -A
watch flux get kustomizations -A
```

## Troubleshooting

**For comprehensive troubleshooting**: Use troubleshooter chat mode or `prompts/troubleshoot-flux.prompt.md`

### Quick Diagnostics

```bash
# Check Flux system
flux check
flux get all -A

# Check specific resources
kubectl get hr -A           # HelmReleases
kubectl get kustomizations -A  # Kustomizations
kubectl get pods -A         # Pods

# View logs
kubectl logs -n flux-system deploy/helm-controller
kubectl logs -n <namespace> <pod-name>

# Check events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

### Common Issues

| Issue | Quick Fix | Full Guide |
|-------|-----------|------------|
| **HelmRelease timeout** | Increase `spec.timeout` | [HelmRelease Recovery](/docs/runbooks/helm-release-recovery.md) |
| **Variable substitution failed** | Check ConfigMap/Secret exists | [Known Issues](/docs/troubleshooting/known-issues.md) |
| **Pod CrashLoopBackOff** | Check logs and events | [Known Issues](/docs/troubleshooting/known-issues.md) |
| **ImagePullBackOff** | Verify image exists and tag | [Known Issues](/docs/troubleshooting/known-issues.md) |

**Complete Knowledge Base**: [Known Issues and Troubleshooting](/docs/troubleshooting/known-issues.md)

### Web-Based Troubleshooting

The cluster supports complete troubleshooting via GitHub Issues and Copilot Chat:

1. Create issue: https://github.com/alecsg77/elysium/issues/new/choose
2. Invoke Copilot: `#file:.github/agents/troubleshooter.agents.md Please investigate and run diagnostics`
3. Review analysis and approve plans: `/approve-plan`
4. Auto-resolution via coding agent

**Complete Workflow**: [Web-Based Troubleshooting](/docs/troubleshooting/web-troubleshooting.md)

## Security

### Secrets
- **Never** commit plain text secrets
- **Always** use Sealed Secrets
- **Backup** sealed-secrets key quarterly
- See [Secret Management](/docs/security/secret-management.md)

### Troubleshooting
- **Treat** all diagnostics as sensitive
- **Redact** secrets, tokens, IPs before sharing
- **Scan** with `rg -n 'password|secret|token|apikey' diagnostics/`
- See [Secure Troubleshooting](/docs/security/secure-troubleshooting.md)

## Operational Best Practices

### Before Committing
- [ ] YAML syntax valid (`yamllint`)
- [ ] Kustomize builds successfully
- [ ] Helm templates render correctly
- [ ] No plain text secrets
- [ ] Resource limits defined
- [ ] Changes tested locally

### Git Workflow

**⚠️ NEVER automatically push without user approval.**

**Required Flow**:
1. Make changes
2. Stage: `git add <files>`
3. Commit: `git commit -m "message"`
4. **STOP and show user what was committed**
5. **Wait for explicit approval**
6. Only push after confirmation: `git push`

**Commit Format**: Follow [Conventional Commits](https://www.conventionalcommits.org/)
- `feat(scope):` New features
- `fix(scope):` Bug fixes
- `docs(scope):` Documentation
- `refactor(scope):` Code restructuring
- `chore(scope):` Maintenance

### Smart Commit Management

When fixing the **most recent unpushed commit**, offer choices:
1. **Amend** - Modify existing commit (cleaner history)
2. **Reset** - Undo commit, keep changes (start over)
3. **New commit** - Separate fix commit (preserves history)

## Related Instruction Files

When working with specific file types, consult:
- `.github/instructions/flux.instructions.md` - Flux patterns
- `.github/instructions/kubernetes.instructions.md` - K8s manifests
- `.github/instructions/kustomize.instructions.md` - Kustomize overlays
- `.github/instructions/helm.instructions.md` - Helm charts
- `.github/instructions/security.instructions.md` - Security practices
- `.github/instructions/testing.instructions.md` - Testing strategies
- `.github/instructions/documentation.instructions.md` - Documentation standards

## Support Resources

### Quick Help Prompts
- **Deploy app**: `prompts/deploy-app.prompt.md`
- **Debug issue**: `prompts/troubleshoot-flux.prompt.md`
- **Review config**: `prompts/review-config.prompt.md`
- **Manage secrets**: `prompts/manage-secrets.prompt.md`

### Documentation
- **[Main Documentation](/docs/README.md)** - Documentation hub
- **[Architecture](/docs/architecture/README.md)** - Cluster architecture
- **[Standards](/docs/standards/README.md)** - Repository standards
- **[Runbooks](/docs/runbooks/README.md)** - Operational procedures
- **[Security](/docs/security/README.md)** - Security guides
- **[Troubleshooting](/docs/troubleshooting/README.md)** - Known issues and workflows

### External Resources
- [Flux Documentation](https://fluxcd.io/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Kustomize Documentation](https://kustomize.io/)

---

**Remember**: This is a GitOps repository - all cluster changes must go through Git. Use references to `/docs/` for authoritative documentation.
