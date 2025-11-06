---
mode: 'agent'
model: Claude Sonnet 4
tools: ['codebase', 'search']
description: 'Review Kubernetes manifests and Flux configurations for best practices'
---

# Review GitOps Configuration

You are reviewing Kubernetes manifests and Flux CD configurations for the Elysium homelab to ensure they follow best practices.

## Review Checklist

### General Manifest Quality

#### YAML Structure
- [ ] Valid YAML syntax (no tabs, proper indentation)
- [ ] Consistent 2-space indentation throughout
- [ ] Document separator `---` between resources
- [ ] Proper use of comments for complex configurations
- [ ] No trailing whitespace

#### Resource Definition
- [ ] `apiVersion` is current (no deprecated APIs)
- [ ] `kind` is correct for the resource type
- [ ] `metadata.name` follows kebab-case convention
- [ ] `metadata.namespace` is explicitly specified
- [ ] Standard labels present: `app.kubernetes.io/name`, `app.kubernetes.io/instance`

### Kubernetes Best Practices

#### Security
- [ ] **NO plain text secrets** in any files
- [ ] Pod security context defined (`runAsNonRoot`, `readOnlyRootFilesystem`)
- [ ] Capabilities dropped appropriately
- [ ] Service accounts explicitly specified (not default)
- [ ] RBAC rules follow least privilege
- [ ] Image pull secrets configured for private registries
- [ ] Network policies defined for network segmentation

#### Resources
- [ ] Resource requests defined for all containers
- [ ] Resource limits defined and reasonable
- [ ] Liveness probes configured appropriately
- [ ] Readiness probes configured appropriately
- [ ] Startup probes for slow-starting apps
- [ ] Graceful shutdown with `preStop` hooks

#### Storage
- [ ] PersistentVolumeClaims use appropriate storage class
- [ ] Volume sizes are specified
- [ ] Access modes are correct
- [ ] Volumes properly mounted in containers

### Flux CD Patterns

#### Kustomization Resources
- [ ] Path points to valid directory
- [ ] Dependencies declared with `dependsOn`
- [ ] Health checks enabled
- [ ] Prune enabled for automatic cleanup
- [ ] Appropriate reconciliation interval
- [ ] Timeout values are reasonable
- [ ] Variable substitution using `postBuild.substituteFrom`

#### HelmRelease Resources
- [ ] Chart version pinned (not using `*` or latest)
- [ ] Source reference is correct
- [ ] Namespace matches intended deployment target
- [ ] Install and upgrade timeouts configured
- [ ] Rollback strategy defined
- [ ] Values structure matches chart schema
- [ ] Secrets referenced via `valuesFrom` when needed

#### GitRepository Sources
- [ ] URL is accessible
- [ ] Branch/ref is specified
- [ ] Authentication configured for private repos
- [ ] Reconciliation interval appropriate

### Helm Chart Values

#### Structure
- [ ] Values follow chart schema
- [ ] Required values are provided
- [ ] Optional values only set when needed
- [ ] No hardcoded environment-specific values in base

#### Images
- [ ] Image repository specified
- [ ] Image tag pinned to specific version
- [ ] Image pull policy appropriate
- [ ] Flux image policy marker present (if auto-update enabled)

#### Configuration
- [ ] ConfigMaps used for non-sensitive config
- [ ] Secrets used for sensitive data
- [ ] Environment variables properly sourced
- [ ] External references validated

### Kustomize Overlays

#### Base Configuration
- [ ] Base resources are environment-agnostic
- [ ] Common labels and annotations defined
- [ ] No environment-specific values

#### Overlay Configuration
- [ ] References base correctly
- [ ] Patches are minimal and targeted
- [ ] Strategic merge patches used appropriately
- [ ] Environment-specific values in overlay only
- [ ] Additional resources properly integrated

### Security Review

- [ ] All secrets are sealed (no plain text)
- [ ] Sealed secrets use correct namespace
- [ ] Secret keys referenced correctly in apps
- [ ] No sensitive data in environment variables
- [ ] No credentials in Git history
- [ ] RBAC permissions appropriate
- [ ] Pod security standards enforced

### Documentation

- [ ] Complex configurations have inline comments
- [ ] README exists for new applications
- [ ] Dependencies documented
- [ ] Configuration options explained
- [ ] Troubleshooting tips included

### Testing Validation

- [ ] Can build locally: `kustomize build <path>`
- [ ] Flux build succeeds: `flux build kustomization <name>`
- [ ] Helm template renders: `helm template <name> <chart> -f values.yaml`
- [ ] YAML validates: `kubeval` or `kubeconform`
- [ ] Security scans pass: `trivy` or `checkov`

## Common Issues to Flag

### Critical Issues ⛔
- Plain text secrets committed to Git
- Missing security contexts
- No resource limits (risk of resource exhaustion)
- Deprecated API versions
- Missing namespace specifications
- Hardcoded credentials or API keys

### High Priority ⚠️
- Missing health probes
- No RBAC configuration
- Insufficient resource requests
- Missing documentation
- Incorrect dependency declarations
- Image using `latest` tag

### Medium Priority ⚡
- Suboptimal resource limits
- Missing labels or annotations
- Inconsistent naming conventions
- Missing NetworkPolicies
- No PodDisruptionBudgets for critical apps

### Low Priority 💡
- Could use more comments
- Could benefit from refactoring
- Documentation could be more detailed
- Could use more specific version pins

## Review Process

1. **Scan for critical security issues first**
2. **Verify Flux resource correctness**
3. **Check Kubernetes best practices**
4. **Review resource specifications**
5. **Validate dependencies and ordering**
6. **Check documentation completeness**
7. **Suggest optimizations and improvements**

## Providing Feedback

When reviewing:
- Be specific about issues found
- Explain why the issue matters
- Provide corrected example or reference
- Link to relevant documentation
- Prioritize issues by severity
- Suggest improvements constructively

Refer to:
- [Kubernetes guidelines](../.github/instructions/kubernetes.instructions.md)
- [Flux patterns](../.github/instructions/flux.instructions.md)
- [Security standards](../.github/instructions/security.instructions.md)
- [Helm best practices](../.github/instructions/helm.instructions.md)
