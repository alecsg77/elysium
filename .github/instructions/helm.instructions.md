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

**IMPORTANT**: Follow the chart selection priority defined in the main [Copilot Instructions - Helm + Kustomize Integration](../copilot-instructions.md#helm--kustomize-integration) section.

### Quick Reference:
1. Official chart from app owner/organization (highest priority)
2. Official documentation recommendation
3. Well-maintained community/vendor charts (Bitnami, Prometheus community, etc.)
4. Official Kustomize manifests
5. onechart generic wrapper - **last resort only**

### Chart Evaluation Criteria:
- Review chart dependencies and resource requirements
- Verify chart compatibility with Kubernetes version
- Check for CRD requirements and install order
- Evaluate chart documentation and community support
- Check last update date and issue activity
- Review chart values.yaml for configuration options

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

### Diagnostic Commands
```bash
# Check HelmRelease status
kubectl get hr -A

# Detailed HelmRelease information
kubectl describe hr <name> -n <namespace>

# View release history
flux get helmreleases -A
helm history <name> -n <namespace>

# Examine Helm Controller logs
kubectl logs -n flux-system deploy/helm-controller | grep <namespace>/<name>

# Debug values
helm get values <name> -n <namespace>

# Verify chart repository
flux get sources helm -A
kubectl describe helmrepository <repo> -n flux-system
```

### Failed HelmRelease Recovery

#### Step 1: Identify Root Cause
1. Check `status.conditions` in HelmRelease for error messages
2. Review Helm controller logs for detailed errors
3. Verify chart source (HelmRepository) is Ready
4. Check valuesFrom references exist (ConfigMaps/Secrets)
5. Examine deployed pod status and logs

#### Step 2: Recovery Strategies

**Reconcile (for transient failures)**
```bash
flux reconcile helmrelease <name> -n <namespace>
```

**Suspend and Fix (for persistent issues)**
```bash
# Suspend to stop retry loop
flux suspend helmrelease <name> -n <namespace>

# Fix configuration in Git
# Commit changes

# Resume after fix
flux resume helmrelease <name> -n <namespace>
```

**Manual Rollback (for failed upgrades)**
```bash
# View history
helm history <name> -n <namespace>

# Rollback to working version
helm rollback <name> <revision> -n <namespace>

# Update HelmRelease in Git to match rolled-back version
```

**Delete and Recreate (last resort)**
```bash
# Delete HelmRelease resource
kubectl delete hr <name> -n <namespace>

# Optionally uninstall Helm release
helm uninstall <name> -n <namespace>

# Fix configuration in Git, commit
# Flux will recreate on next reconciliation
```

#### Step 3: Common Issue Resolutions

**Timeout Errors**
- Increase `spec.timeout` in HelmRelease (default 5m)
- Check pod startup logs for slow initialization
- Verify resource availability (CPU, memory, storage)
- Check init containers and volume mounts

**Values Validation Errors**
- Test locally: `helm template <chart> -f values.yaml`
- Compare values structure with chart's `values.schema.json`
- Verify all required values are provided
- Check data types match schema expectations

**CRD Not Found**
- Install CRDs first via separate HelmRelease with dependency
- Use `spec.install.crds: CreateReplace` in HelmRelease
- Ensure CRD-providing operator is installed and Ready

**Image Pull Failures**
- Verify image exists: `docker pull <image>:<tag>`
- Check image pull secrets are configured
- Test registry access from cluster
- Verify image tag is correct

### Prevention Best Practices
- **Pin versions**: Use explicit chart versions, avoid `latest`
- **Test values**: Validate with `helm template` before deploying
- **Set timeouts**: Base on historical deployment times + buffer
- **Configure retries**: `spec.install.remediation.retries: 3`
- **Enable rollback**: `spec.upgrade.remediation.remediateLastFailure: true`
- **Monitor proactively**: Set up alerts for failed HelmReleases

## Web-Based Troubleshooting for HelmReleases

For comprehensive HelmRelease diagnostics and automated resolution, use the GitHub Issues-based workflow:

### Quick Start

1. **Create Issue**: https://github.com/alecsg77/elysium/issues/new/choose
   - Select "🐛 Bug Report" for known HelmRelease failures
   - Provide HelmRelease name, namespace, error message from `kubectl describe hr`

2. **Invoke Diagnostics**: In GitHub Copilot Chat on issue page
   ```
   #file:.github/agents/troubleshooter.agents.md
   Please investigate this HelmRelease failure
   ```

3. **Automated Diagnostic Collection**:
   - HelmRelease status conditions and inventory
   - Helm controller logs filtered by namespace/release
   - Chart source (HelmRepository) status
   - Values from ConfigMaps/Secrets
   - Deployed pod status and logs
   - Kubernetes events timeline

4. **Root Cause Analysis**: Copilot identifies distinct issues and creates bug per root cause

5. **Approve Resolution**: Review proposed fixes (file changes, validation steps) and approve

6. **Automated Implementation**: Coding agent creates PR, coordinator validates via Flux reconciliation

### Common HelmRelease Patterns in Knowledge Base

- **HelmRelease Timeout**: Increase spec.timeout, check pod startup
- **Chart Not Found**: Verify HelmRepository status, chart name/version
- **Values Validation Failed**: Template locally, check schema compatibility
- **CRD Missing**: Install CRDs first, add dependency ordering
- **Image Pull Error**: Verify registry access, image tag exists

### Circuit Breaker Protection

- Automatic retry with adjusted plans (up to 3 attempts)
- Tracks attempts with `resolution-attempt:N` labels
- Manual intervention after 3 failures
- Reset with `/reset-attempts` after manual fixes

### Additional Resources

- **Troubleshooting Guide**: `.github/TROUBLESHOOTING.md`
- **Known Issues Database**: `.github/KNOWN_ISSUES.md`
- **Copilot Instructions**: `.github/copilot-instructions.md` - See "Web-Based Troubleshooting Workflow"
