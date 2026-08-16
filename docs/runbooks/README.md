# Runbooks

Operational procedures and playbooks for common cluster management tasks.

## Purpose

This directory contains step-by-step procedures for routine operational tasks. Each runbook should be standalone and actionable.

## Contents

### Application and Infrastructure Management
- **[Adding or Changing an Application](add-application.md)** - Complete workflow for deploying new apps or modifying existing ones using Flux CD, Kustomize, and Helm
- **[Adding or Changing an Infrastructure Component](add-infrastructure-component.md)** - Controller/config ownership, cluster parameter wrappers, secret delivery, validation, and rollback
- **[HelmRelease Recovery](helm-release-recovery.md)** - Systematic procedures for recovering from failed HelmRelease deployments (timeouts, values errors, CRD issues, MongoDB failures)
- **[Resource Optimization](resource-optimization.md)** - Procedures for optimizing cluster resource usage and resolving resource constraints
- **[tsidp OIDC for Headlamp](tsidp-sso.md)** - Per-user Headlamp OIDC and Kubernetes RBAC rollout
- **[Gitless ResourceSet Image Automation](resourceset-image-automation.md)** - Gitless workload image updates, safety gates, and rollback pins

### Cluster Operations
- **[Backup and Restore](backup-and-restore.md)** - Reusable encrypted PVC backup contract and restore drills
- **[Flux Web UI with tsidp OIDC](flux-web-ui.md)** - Private-domain Flux dashboard, OIDC client sealing, read-only RBAC, and rollback
- **[Migrating Flux to Flux Operator](flux-operator-migration.md)** - Staged, zero-downtime migration and optional internal MCP rollout

Examples:
- Flux reconciliation and forced deploy
- Secret rotation procedures
- Scaling applications

## Runbook Standards

Each runbook should include:
- **Prerequisites**: Required tools, access, and knowledge
- **Overview**: Brief description and estimated time
- **Step-by-step procedure**: Clear, numbered steps with commands
- **Validation**: How to verify success at each stage
- **Troubleshooting**: Common issues and solutions
- **Related Documentation**: Links to relevant standards and guides
- **Checklist**: Pre-action and post-action verification items

## Contributing

When adding a new runbook:
1. Use the template structure above
2. Test the procedure before documenting
3. Include example commands and expected output
4. Add validation steps after each major action
5. Document common failure scenarios
6. Update this README with a link and category
7. Link to relevant standards in `/docs/standards/`
