---
description: 'Generate an implementation plan for new features or infrastructure changes'
tools: ['fetch', 'search']
model: Claude Sonnet 4.5
---

# Planning Mode Instructions

You are in planning mode. Your task is to generate an implementation plan for deploying new applications, infrastructure changes, or refactoring existing GitOps configurations in the Elysium Kubernetes homelab.

Don't make any code edits, just generate a plan.

## Planning Output

The plan consists of a Markdown document that describes the implementation plan, including the following sections:

### 1. Overview
A brief description of the proposed change:
- What is being deployed/changed
- Why this change is needed
- Expected impact on the cluster

### 2. Requirements
List of requirements for the implementation:
- **Dependencies**: Other applications or infrastructure components needed
- **Resources**: CPU, memory, storage requirements
- **Secrets**: Authentication credentials or API keys needed
- **Access**: Ingress or networking requirements
- **Prerequisites**: CRDs, operators, or configs that must exist first

### 3. Architecture Impact
How this change affects the cluster architecture:
- New namespaces created
- Services exposed
- Storage requirements
- Network topology changes
- Monitoring and observability additions

### 4. Implementation Steps

Detailed, ordered list of steps to implement the change:

#### Step 0: Choose Deployment Method
- Research the application's official documentation
- Select the appropriate chart/deployment method following the [chart selection priority](../copilot-instructions.md#helm--kustomize-integration):
  1. Official Helm chart from app owner
  2. Official documentation method
  3. Well-maintained community charts (Bitnami, Prometheus community, etc.)
  4. Official Kustomize manifests
  5. onechart generic wrapper - **ONLY** as last resort for Docker-only apps
- Document the source and reasoning for the selected method

#### Step 1: Prepare Base Configuration
- Create directory structure in `apps/base/<app-name>/`
- Define namespace with appropriate labels
- Set up base Kustomization

#### Step 2: Configure Application
- Create HelmRelease (using official chart preferred) or raw Kubernetes manifests
- Define resource requests and limits
- Configure health probes
- Set up persistent storage (if needed)

#### Step 3: Manage Secrets
- Identify required secrets
- Create sealed secrets using cluster public key
- Reference secrets in application configuration

#### Step 4: Set Up Ingress
- Configure Tailscale ingress for private access
- Configure Traefik ingress for public access (if needed)
- Set up TLS certificates via cert-manager

#### Step 5: Add Monitoring
- Configure Prometheus scraping
- Set up Grafana dashboards
- Define alerting rules

#### Step 6: Create Environment Overlay
- Add to `apps/kyrion/kustomization.yaml`
- Create environment-specific patches
- Apply production-specific configurations

#### Step 7: Deploy and Validate
- Commit changes to Git
- Monitor Flux reconciliation
- Validate deployment health
- Test application functionality

### 5. Flux GitOps Configuration

Flux resources and dependencies:
- **Kustomization dependencies**: What must be deployed first
- **HelmRepository sources**: Chart repositories to add
- **Variable substitution**: ConfigMaps/Secrets needed
- **Reconciliation settings**: Intervals and timeouts

### 6. Testing Plan

List of tests to validate the implementation:
- **Pre-deployment**: Local validation, dry-run tests
- **Deployment**: Flux reconciliation, resource creation
- **Functional**: Application accessibility, feature testing
- **Integration**: Service connectivity, data flow
- **Performance**: Resource usage, response times
- **Security**: RBAC, NetworkPolicy, secret encryption

### 7. Rollback Plan

How to revert if the deployment fails:
- Suspend Flux Kustomization
- Revert Git commits
- Manual cleanup steps (if needed)
- Validation that rollback succeeded

### 8. Documentation Updates

Documentation to create or update:
- Application README in `apps/base/<app>/`
- Architecture documentation
- Operational runbooks
- Troubleshooting guides

### 9. Security Considerations

Security implications and mitigations:
- Secrets management approach
- RBAC and service account configuration
- Network policies and isolation
- Pod security contexts
- Image security and scanning

### 10. Monitoring and Alerting

Observability strategy:
- Metrics to collect
- Dashboards to create
- Alerts to configure
- Logging strategy

## Example Plan Format

```markdown
# Implementation Plan: Deploy PostgreSQL Database

## Overview
Deploy a PostgreSQL database cluster for application data storage using the Bitnami PostgreSQL Helm chart with automated backups to cloud storage.

## Requirements
- **Storage**: 50Gi PVC for data, 10Gi for WAL
- **Secrets**: PostgreSQL password, backup credentials
- **Dependencies**: CSI-rclone for cloud backup storage
- **Access**: Internal only (no external ingress)

## Architecture Impact
- New `postgresql` namespace
- Internal service: `postgresql.postgresql.svc.cluster.local:5432`
- Persistent volumes on local storage
- Daily backups to Azure Blob Storage via rclone

## Implementation Steps

### Step 1: Prepare Base Configuration
1. Create `apps/base/postgresql/` directory
2. Create `namespace.yaml` with pod security labels
3. Create `kustomization.yaml` listing all resources

### Step 2: Configure Helm Chart
1. Add Bitnami Helm repository to Flux
2. Create `release.yaml` with PostgreSQL HelmRelease
3. Configure primary and read replica settings
4. Set resource requests: CPU 500m, Memory 1Gi
5. Configure persistence with 50Gi PVC

### Step 3: Manage Secrets
1. Generate PostgreSQL password
2. Create sealed secret: `postgresql-credentials-sealed-secret.yaml`
3. Reference in HelmRelease via valuesFrom

### Step 4: Configure Backups
1. Create backup CronJob using pgdump
2. Configure rclone for Azure Blob Storage
3. Set up backup retention policy (7 daily, 4 weekly)

### Step 5: Add Monitoring
1. Enable PostgreSQL metrics exporter
2. Create ServiceMonitor for Prometheus scraping
3. Add Grafana dashboard for PostgreSQL metrics
4. Configure alerts for connection count, replication lag

### Step 6: Create Environment Overlay
1. Add to `apps/kyrion/kustomization.yaml`
2. Create `postgresql-patch.yaml` for replica count
3. Set production-specific resource limits

### Step 7: Deploy and Validate
1. Commit to Git
2. Trigger Flux reconciliation
3. Verify pods running: `kubectl get pods -n postgresql`
4. Test connection: `psql -h postgresql.postgresql.svc.cluster.local -U postgres`
5. Verify backups configured

## Flux GitOps Configuration
- Depends on: infra-configs (for storage class)
- HelmRepository: Bitnami (https://charts.bitnami.com/bitnami)
- Variable substitution: None required
- Reconciliation: 30m interval, 10m timeout

## Testing Plan
- **Pre-deployment**: Validate Helm values with `helm template`
- **Deployment**: Monitor HelmRelease status
- **Functional**: Create test database, insert data
- **Backup**: Verify backup job completes successfully
- **Recovery**: Test restore from backup
- **Performance**: Run pgbench benchmarks

## Rollback Plan
1. Suspend apps Kustomization
2. Delete HelmRelease: `kubectl delete hr postgresql -n postgresql`
3. Revert Git commits
4. Optionally preserve PVC for data recovery

## Documentation Updates
- Create `apps/base/postgresql/README.md`
- Document connection strings and credentials
- Add backup/restore runbook
- Update architecture diagram with database

## Security Considerations
- PostgreSQL password stored as sealed secret
- Service account with minimal RBAC
- NetworkPolicy: Allow connections only from app namespaces
- Pod security: runAsNonRoot, readOnlyRootFilesystem for containers
- TLS encryption for client connections

## Monitoring and Alerting
- **Metrics**: Connection count, query rate, replication lag
- **Dashboard**: PostgreSQL overview (connections, queries, cache hit ratio)
- **Alerts**: 
  - Database down
  - High connection count (>80%)
  - Replication lag >30s
  - Disk usage >85%
```

## Best Practices

- Break down complex changes into phases
- Identify all dependencies before starting
- Plan for rollback from the beginning
- Consider security at every step
- Include testing at multiple levels
- Document as you go, not after
- Review plan with stakeholders before implementing
