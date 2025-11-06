---
applyTo: "**/*.yaml,**/*.yml,**/*.sh"
description: "Testing strategies for GitOps infrastructure"
---

# Testing Guidelines for GitOps Infrastructure

## Pre-Commit Testing
- Validate YAML syntax with `yamllint` before committing
- Check Kubernetes manifest syntax with `kubectl apply --dry-run=client`
- Build Kustomize overlays locally: `kustomize build <path>`
- Test Flux build: `flux build kustomization <name> --path <path>`
- Run `helm template` to validate HelmRelease values
- Use `kubeconform` or `kubeval` for schema validation

## Manifest Validation
- Ensure all resources have required fields
- Verify label and selector consistency
- Check resource naming conventions
- Validate namespace references
- Confirm dependency declarations are accurate
- Test variable substitution with sample values

## Kustomize Testing
- Build each overlay independently
- Verify patches apply correctly without errors
- Check for resource conflicts or duplicates
- Validate generated ConfigMaps and Secrets
- Test strategic merge patch results
- Confirm common labels and annotations applied

## Helm Chart Testing
- Render templates with various value combinations
- Validate chart dependencies resolve correctly
- Test with minimum and maximum value ranges
- Verify NOTES.txt renders helpful information
- Check for hardcoded values that should be configurable
- Validate hooks execute in correct order

## Flux Reconciliation Testing
- Use `flux reconcile source git flux-system` to trigger immediate sync
- Monitor reconciliation with `flux get kustomizations -A`
- Check resource creation with `kubectl get all -n <namespace>`
- Verify health checks pass: `flux get helmreleases -A`
- Test suspend/resume functionality
- Validate dependency ordering works as expected

## Integration Testing
- Deploy to test/staging environment before production
- Verify application functionality post-deployment
- Test service connectivity and networking
- Validate persistent volume claims work correctly
- Check resource quotas and limits enforced
- Test pod scheduling and node affinity

## Secret Management Testing
- Verify sealed secrets decrypt correctly in cluster
- Test secret rotation procedures
- Validate secret references in pods work
- Check secret permissions and access control
- Test secret backup and restore procedures

## Security Testing
- Scan manifests with `trivy` or `checkov`
- Validate RBAC policies are restrictive
- Check pod security contexts enforced
- Test NetworkPolicy rules block unexpected traffic
- Verify image pull secrets work correctly
- Audit for hardcoded secrets or sensitive data

## Performance Testing
- Monitor reconciliation loop performance
- Check Flux controller resource usage
- Validate image update automation speed
- Test large-scale deployments
- Monitor Git repository clone times
- Profile kustomize build times for complex overlays

## Upgrade Testing
- Test Kubernetes version upgrades in staging
- Validate Flux component upgrades
- Test Helm chart version upgrades
- Check for deprecated API versions
- Verify CRD upgrades don't break existing resources

## Rollback Testing
- Test HelmRelease rollback on failure
- Verify Flux can recover from bad commits
- Test manual rollback procedures
- Validate backup restore processes
- Check for data loss during rollbacks

## Monitoring and Alerting Testing
- Verify Prometheus scrapes metrics correctly
- Test alert rules trigger as expected
- Validate Grafana dashboards display data
- Check notification channels work
- Test log aggregation and searching

## Documentation Testing
- Verify README instructions are accurate
- Test documented procedures end-to-end
- Validate runbooks for common tasks
- Check for outdated documentation
- Ensure diagrams reflect current architecture

## Automated Testing Tools
- **yamllint**: YAML syntax and style checking
- **kubeval/kubeconform**: Kubernetes schema validation  
- **kustomize build**: Overlay rendering
- **flux build**: Flux manifest building
- **helm lint**: Chart validation
- **helm template**: Template rendering
- **trivy/checkov**: Security scanning
- **conftest**: Policy testing with Rego

## CI/CD Pipeline Testing
- Validate GitHub Actions workflows execute correctly
- Test artifact generation and publishing
- Verify automated deployments work
- Check notification integrations
- Test failure handling and retries

## Testing Checklist
- [ ] YAML syntax valid
- [ ] Kustomize builds successfully
- [ ] Helm templates render correctly
- [ ] No hardcoded secrets
- [ ] Resource names follow conventions
- [ ] Labels and selectors consistent
- [ ] Dependencies declared correctly
- [ ] Security contexts configured
- [ ] Resource limits defined
- [ ] Health checks configured
- [ ] Documentation updated
- [ ] Changes tested in staging
