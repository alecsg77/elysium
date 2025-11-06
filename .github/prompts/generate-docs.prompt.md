---
mode: 'agent'
model: Claude Sonnet 4
tools: ['codebase', 'fetch']
description: 'Generate comprehensive documentation for applications and infrastructure'
---

# Generate Documentation

You are helping create comprehensive documentation for applications and infrastructure in the Elysium Kubernetes homelab.

## What to Document

Ask the user what type of documentation is needed:
1. **Application README** - Document a specific application
2. **Architecture Overview** - High-level system documentation
3. **Operational Runbook** - Step-by-step procedures
4. **Troubleshooting Guide** - Common issues and solutions
5. **API Documentation** - Service endpoints and APIs

## Application README Template

Create `apps/base/<app-name>/README.md`:

```markdown
# <Application Name>

Brief description of what this application does and its purpose in the homelab.

## Overview

- **Purpose**: Why this application exists
- **Version**: Current version deployed
- **Dependencies**: Other services or infrastructure required
- **Resources**: CPU, memory, storage requirements

## Architecture

[Optional: mermaid diagram of application components]

\`\`\`mermaid
graph LR
    A[Ingress] --> B[Service]
    B --> C[Deployment]
    C --> D[PVC Storage]
\`\`\`

## Configuration

### Helm Chart
- **Repository**: <helm-repo-url>
- **Chart**: <chart-name>
- **Version**: <chart-version>

### Key Configuration Options

| Option | Description | Default | Override Location |
|--------|-------------|---------|-------------------|
| `replicas` | Number of pods | 1 | `apps/kyrion/<app>-patch.yaml` |
| `persistence.size` | Storage size | 10Gi | base values |

### Environment Variables

- `VARIABLE_NAME` - Description and purpose
- Sourced from: `cluster-vars` ConfigMap or `<app>-secret` Secret

### Secrets

Secrets managed via Sealed Secrets:
- `<app>-secret.yaml` - Contains: API keys, passwords, tokens
- Creation: See `../../.github/prompts/manage-secrets.prompt.md`

## Deployment

Deployed automatically via Flux CD from Git repository.

### Manual Reconciliation
\`\`\`bash
flux reconcile kustomization apps
kubectl get hr <app-name> -n <namespace>
\`\`\`

### Access

- **Internal**: http://<app-name>.<namespace>.svc.cluster.local
- **Tailscale Ingress**: http://<app-name>.ts.net (if configured)
- **External**: https://<app-name>.example.com (if configured)

## Storage

- **Type**: PersistentVolumeClaim
- **Storage Class**: local-path
- **Existing Claim**: pvc-storage (shared)
- **Mount Path**: /data
- **Sub Path**: <app-name>-data

## Monitoring

- **Metrics**: Exposed at `/metrics` on port 8080
- **Grafana Dashboard**: <dashboard-name>
- **Prometheus ServiceMonitor**: Configured in monitoring namespace
- **Logs**: Aggregated in Loki, accessible via Grafana

## Backup and Recovery

### Backup Procedure
1. Suspend Flux reconciliation: `flux suspend kustomization apps`
2. Scale down application: `kubectl scale deployment/<app> --replicas=0 -n <namespace>`
3. Backup PVC data: `kubectl cp <namespace>/<pod>:/data ./backup`
4. Resume: `flux resume kustomization apps`

### Restore Procedure
1. Follow backup procedure steps 1-2
2. Restore data: `kubectl cp ./backup <namespace>/<pod>:/data`
3. Scale up and resume

## Upgrading

### Chart Version Upgrade
1. Update chart version in `apps/base/<app>/release.yaml`
2. Review chart changelog for breaking changes
3. Test in staging environment first (if available)
4. Commit changes to Git
5. Monitor deployment: `kubectl get hr <app> -n <namespace> -w`

### Application Updates

Application images updated automatically via Flux ImageUpdateAutomation when new versions are available.

## Troubleshooting

### Pod Not Starting
\`\`\`bash
# Check pod status
kubectl get pods -n <namespace>

# View pod events
kubectl describe pod <pod-name> -n <namespace>

# Check logs
kubectl logs -n <namespace> <pod-name>
\`\`\`

### Configuration Issues
- Verify ConfigMap: `kubectl get cm <app>-config -n <namespace> -o yaml`
- Verify Secret: `kubectl get secret <app>-secret -n <namespace>`
- Check HelmRelease values: `helm get values <app> -n <namespace>`

### Common Errors

**Error: ImagePullBackOff**
- Check image name and tag in values
- Verify image registry is accessible
- Check image pull secrets configured

**Error: CrashLoopBackOff**
- Check application logs for startup errors
- Verify environment variables are correct
- Check resource limits not too restrictive

## Links

- [Official Documentation](<upstream-docs-url>)
- [Helm Chart Repository](<chart-repo-url>)
- [Security Guidelines](../../.github/instructions/security.instructions.md)
- [Flux Patterns](../../.github/instructions/flux.instructions.md)
```

## Architecture Documentation Template

Create `docs/architecture/<topic>.md`:

```markdown
# <Architecture Topic>

## Overview

High-level description of the architectural component or pattern.

## Components

### Component 1
- **Purpose**: What it does
- **Technology**: What implements it
- **Location**: Where it's deployed

\`\`\`mermaid
graph TB
    A[Component A] --> B[Component B]
    B --> C[Component C]
\`\`\`

## Design Decisions

### Why This Approach
- Rationale for architecture decisions
- Trade-offs considered
- Alternatives evaluated

## Implementation Details

Technical specifics of how the architecture is implemented.

## Interactions

How components communicate and depend on each other.

## Security Considerations

Security boundaries, access controls, and threat model.

## Monitoring and Observability

How to monitor the architecture components.

## Future Improvements

Potential enhancements or refactoring opportunities.
```

## Runbook Template

Create `docs/runbooks/<task>.md`:

```markdown
# <Task Name> Runbook

## Overview
What this procedure accomplishes and when to use it.

## Prerequisites
- Access requirements
- Tools needed
- Knowledge requirements

## Procedure

### Step 1: <Step Name>
Detailed instructions for the step.

\`\`\`bash
# Commands to execute
command --options
\`\`\`

Expected output:
\`\`\`
Output to look for
\`\`\`

### Step 2: <Step Name>
Continue with subsequent steps...

## Verification
How to verify the procedure succeeded.

## Rollback
How to undo changes if something goes wrong.

## Troubleshooting
Common issues encountered during this procedure.
```

## Best Practices

- Use clear, concise language
- Include practical examples
- Add diagrams for complex concepts
- Link to related documentation
- Keep documentation close to code
- Update docs when code changes
- Test commands before documenting
- Include both success and failure scenarios

Refer to [Documentation standards](../.github/instructions/documentation.instructions.md) for complete guidelines.
