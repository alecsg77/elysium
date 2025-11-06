---
applyTo: "apps/**/*.yaml,infrastructure/**/*.yaml,monitoring/**/*.yaml"
description: "Helm chart configuration and management in Flux"
---

# Helm Best Practices for Flux

## General Guidelines
- Use HelmRelease CRDs instead of direct Helm CLI commands
- Pin chart versions explicitly for reproducibility
- Organize values using base/overlay pattern with Kustomize
- Leverage `valuesFrom` for dynamic configuration injection
- Test chart changes in isolated environments before production

## HelmRelease Structure
- Place HelmRelease in `apps/base/<app>/release.yaml`
- Create environment-specific patches in `apps/<env>/`
- Use descriptive release names matching the application
- Specify target namespace explicitly
- Configure appropriate service account and RBAC

## Chart Selection
- Prefer official or well-maintained charts
- Review chart dependencies and resource requirements
- Verify chart compatibility with Kubernetes version
- Check for CRD requirements and install order
- Evaluate chart documentation and community support

## Values Management
- Keep base values minimal and environment-agnostic
- Use Kustomize patches for environment overrides
- Reference ConfigMaps/Secrets via `valuesFrom`
- Structure values hierarchically for clarity
- Document custom values with inline comments

## Version Management
- Use semantic versioning constraints appropriately
- Test upgrades in non-production first
- Review chart CHANGELOG before upgrading
- Set `spec.upgrade.force: false` to prevent forced upgrades
- Configure rollback on failure with reasonable thresholds

## Dependencies
- Declare chart dependencies in `dependsOn` field
- Ensure CRDs are installed before dependent charts
- Use Flux Kustomization dependencies for orchestration
- Wait for prerequisite resources to be ready
- Consider startup order for tightly coupled services

## Lifecycle Management
- Configure install/upgrade timeouts appropriately
- Set remediation strategies for failed deployments
- Use `spec.upgrade.remediation.retries` for automatic recovery
- Configure `cleanupOnFail: true` for failed installs
- Enable `atomic: true` for rollback on upgrade failure

## Resource Management
- Override default resource requests/limits as needed
- Configure pod disruption budgets for availability
- Set appropriate replica counts per environment
- Use horizontal pod autoscaling when applicable
- Configure persistent volume claims correctly

## Security
- Use specific service accounts (avoid default)
- Set pod security contexts in values
- Configure network policies through chart values
- Use encrypted secrets for sensitive values
- Enable RBAC and least-privilege access

## Monitoring and Observability
- Enable Prometheus metrics via chart values
- Configure health check endpoints
- Set up service monitors or pod monitors
- Add custom dashboards via ConfigMaps
- Configure alerting rules as needed

## Testing
- Validate HelmRelease with `flux reconcile`
- Use `helm template` for local validation
- Test with different value combinations
- Verify resource creation and readiness
- Check for drift with `flux diff`

## Common Patterns

### External Secrets
```yaml
spec:
  valuesFrom:
    - kind: Secret
      name: app-secret
      valuesKey: values.yaml
```

### Image Override
```yaml
spec:
  values:
    image:
      repository: custom-registry/image
      tag: v1.2.3
```

### Resource Limits
```yaml
spec:
  values:
    resources:
      limits:
        cpu: 1000m
        memory: 512Mi
      requests:
        cpu: 100m
        memory: 128Mi
```

## Troubleshooting
- Check HelmRelease status: `kubectl get hr -A`
- View release history: `flux get helmreleases`
- Examine Helm Controller logs for errors
- Use `helm get values <release>` to debug values
- Verify chart repository accessibility
