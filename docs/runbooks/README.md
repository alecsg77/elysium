# Runbooks

Operational procedures and playbooks for common cluster management tasks.

## Purpose

This directory contains step-by-step procedures for routine operational tasks. Each runbook should be standalone and actionable.

## Contents

### Application Management
- **[Adding or Changing an Application](add-application.md)** - Complete workflow for deploying new apps or modifying existing ones using Flux CD, Kustomize, and Helm
- **[HelmRelease Recovery](helm-release-recovery.md)** - Systematic procedures for recovering from failed HelmRelease deployments (timeouts, values errors, CRD issues, MongoDB failures)
- **[Resource Optimization](resource-optimization.md)** - Procedures for optimizing cluster resource usage and resolving resource constraints

### Cluster Operations
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
