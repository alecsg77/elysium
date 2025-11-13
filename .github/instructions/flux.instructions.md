---
applyTo: "clusters/**/*.yaml,infrastructure/**/*.yaml,apps/**/*.yaml,monitoring/**/*.yaml"
description: "Flux CD GitOps patterns and conventions"
---

# Flux CD GitOps Conventions

## Core Principles
- All cluster state managed through Git (single source of truth)
- Flux automatically reconciles cluster state with Git
- Use dependency chains to ensure ordered deployment
- Leverage variable substitution for environment-specific values
- Encrypt sensitive data with Sealed Secrets

## Flux Resource Types

### GitRepository
- Point to the primary repository branch (typically `main`)
- Set appropriate reconciliation intervals (balance freshness vs. load)
- Use SSH authentication with deploy keys for private repositories
- Include `.sourceignore` to exclude unnecessary files

### Kustomization
- Define clear dependency chains with `dependsOn`
- Use `postBuild.substituteFrom` for variable injection
- Set health checks with appropriate timeouts
- Use `prune: true` for automatic resource cleanup
- Configure retry intervals and timeout values appropriately

### HelmRepository
- Reference stable chart repositories
- Set update intervals based on release frequency
- Use HTTPS sources when possible

### HelmRelease
- Specify chart version explicitly (avoid `latest`)
- Use `valuesFrom` for ConfigMap/Secret value injection
- Configure rollback strategies and failure thresholds
- Set appropriate install/upgrade timeouts
- Use `dependsOn` for deployment ordering

## Dependency Patterns
Follow the standard dependency hierarchy:
1. Infrastructure Controllers (CRDs, operators)
2. Infrastructure Configs (cluster-wide settings)
3. Application deployments

Example dependency chain:
```yaml
spec:
  dependsOn:
    - name: infra-controllers
      namespace: flux-system
```

## Variable Substitution
Reference ConfigMaps and Secrets for environment variables:
```yaml
spec:
  postBuild:
    substituteFrom:
      - kind: ConfigMap
        name: cluster-vars
      - kind: Secret
        name: cluster-secret-vars
```

Use variables in manifests: `${VARIABLE_NAME}`

## Secret Management
- Never commit plain text secrets
- Use `kubeseal` to encrypt secrets with cluster public key
- Store sealed secrets in Git as `*-sealed-secret.yaml`
- Reference sealed secrets in Flux resources via `valuesFrom`

## Image Automation
- Create ImageRepository resources for container registries
- Define ImagePolicy with version constraints (semver, regex)
- Use ImageUpdateAutomation to commit tag updates to Git
- Add policy markers in manifests: `# {"$imagepolicy": "namespace:policy-name"}`

## Helm Integration
- Prefer HelmRelease over direct Helm commands
- Use Kustomize patches for environment-specific overrides
- Structure values in base directory with environment overlays
- Leverage `valuesFrom` for dynamic value injection

## Reconciliation Control
- Use `suspend: true` to pause reconciliation temporarily
- Trigger immediate reconciliation with `flux reconcile`
- Monitor Flux events with `flux events`
- Check resource status with `flux get all`

## Performance Optimization
- Set appropriate reconciliation intervals (avoid too frequent)
- Use `.sourceignore` to skip large unnecessary files
- Limit scope of Kustomizations to specific paths
- Use `--wait` flags judiciously in workflows

## Error Handling

### Retry and Timeout Configuration
- Configure retry intervals with exponential backoff: `retryInterval: 2m`
- Set appropriate timeout values for large deployments: `timeout: 10m`
- Use health checks and status conditions: `wait: true`
- Monitor Flux controller logs for issues: `kubectl logs -n flux-system deploy/kustomize-controller`

### Common Error Patterns

#### Kustomization Failures
| Error | Cause | Resolution |
|-------|-------|------------|
| `Path not found` | Invalid `spec.path` | Verify directory exists in Git repository |
| `YAML parse error` | Syntax error in manifests | Run `yamllint` on affected files |
| `Variable substitution failed` | Missing ConfigMap/Secret | Ensure substituteFrom references exist |
| `Dependency not ready` | Blocking dependency failed | Fix dependency first, then reconcile |
| `Resource conflict` | Resource already exists | Check for conflicting resources, adjust configuration |

#### HelmRelease Failures
| Error | Cause | Resolution |
|-------|-------|------------|
| `Install timeout` | Slow pod startup | Increase timeout, check pod logs |
| `Chart not found` | Invalid chart reference | Verify HelmRepository, chart name, version |
| `Values validation` | Invalid values structure | Compare with chart schema, fix values |
| `CRD not found` | Missing prerequisites | Install CRDs first, use dependsOn |
| `Upgrade failed` | Breaking changes | Review chart CHANGELOG, adjust values, or rollback |

### Recovery Procedures

#### Force Reconciliation
```bash
# Reconcile Git source
flux reconcile source git flux-system

# Reconcile Kustomization
flux reconcile kustomization <name>

# Reconcile HelmRelease
flux reconcile helmrelease <name> -n <namespace>
```

#### Suspend for Investigation
```bash
# Pause reconciliation
flux suspend kustomization <name>

# Fix issues, test locally
kustomize build <path>

# Resume when ready
flux resume kustomization <name>
```

#### Dependency Chain Troubleshooting
```bash
# Check dependency status
kubectl get kustomization -n flux-system

# Visualize dependencies
kubectl get kustomization <name> -o yaml | yq '.spec.dependsOn'

# Reconcile from root
flux reconcile source git flux-system
flux reconcile kustomization infra-controllers
flux reconcile kustomization infra-configs
flux reconcile kustomization apps
```

### Health Check Best Practices
- Set `wait: true` to ensure readiness before marking success
- Configure `healthChecks` for critical Deployments/StatefulSets
- Use appropriate timeouts based on historical deployment times
- Monitor `status.conditions` for detailed health information

## Best Practices
- Keep Flux components up to date
- Use separate Kustomizations for logical component groups
- Document dependencies clearly in README files
- Test changes in non-production environments first
- Use Flux notifications for alerting on failures
