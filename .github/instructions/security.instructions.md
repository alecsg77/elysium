---
applyTo: "**/*.yaml,**/*.yml,**/*.sh"
description: "Security best practices for GitOps infrastructure"
---

# Security Best Practices

## Secret Management
- **NEVER** commit plain text secrets to Git repository
- Use Bitnami Sealed Secrets for encrypting sensitive data
- Encrypt secrets with cluster public key: `etc/certs/pub-sealed-secrets.pem`
- Store encrypted secrets as `*-sealed-secret.yaml` files
- Use `kubeseal` CLI to create sealed secrets from stdin
- Rotate secrets regularly and update sealed versions
- Audit secret access patterns in cluster logs

## Sealed Secrets Workflow
```bash
# Create sealed secret (never commit the input)
echo -n "secret-value" | kubectl create secret generic app-secret \
  --dry-run=client --from-file=key=/dev/stdin -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml > sealed-secret.yaml
```

## RBAC and Service Accounts
- Create dedicated ServiceAccounts for each application
- Follow principle of least privilege for permissions
- Avoid using default ServiceAccount
- Define explicit Role and RoleBinding per namespace
- Use ClusterRole only when truly cluster-wide access needed
- Review and audit RBAC policies regularly
- Document required permissions explicitly

## Pod Security
- Set security contexts for all pods and containers
- Use `runAsNonRoot: true` to prevent root execution
- Set `readOnlyRootFilesystem: true` when possible
- Drop unnecessary Linux capabilities
- Define `allowPrivilegeEscalation: false`
- Use Pod Security Standards (restricted profile preferred)
- Scan container images for vulnerabilities regularly

## Network Security
- Implement NetworkPolicies for pod-to-pod communication
- Default to deny-all, explicitly allow required traffic
- Use namespace isolation for multi-tenant workloads
- Restrict egress traffic to known destinations
- Use Tailscale for secure external access
- Enable TLS for all internal service communication
- Configure ingress with proper TLS certificates

## Image Security
- Use specific image tags (avoid `latest`)
- Pull images from trusted registries only
- Sign and verify container images
- Scan images for CVEs before deployment
- Use private registries for sensitive workloads
- Implement image pull secrets correctly
- Enable image provenance verification

## Secrets in Environment Variables
- Prefer volume mounts over environment variables for secrets
- Use `valueFrom.secretKeyRef` when env vars required
- Avoid logging environment variables in application code
- Don't expose secrets in pod descriptions or events
- Use Flux variable substitution for non-sensitive configs only

## Access Control
- Use Tailscale for private network overlay
- Restrict kubectl access to authorized users
- Implement audit logging for cluster access
- Use context-aware access policies
- Enable MFA for administrative access
- Rotate kubeconfig credentials periodically

## GitOps Security
- Protect main branch with required reviews
- Use signed commits for critical changes
- Implement branch protection rules
- Audit Git access logs regularly
- Use separate repositories for sensitive workloads
- Enable GitHub security scanning and Dependabot

## Certificate Management
- Use cert-manager for automated TLS certificate lifecycle
- Configure Let's Encrypt for public endpoints
- Use appropriate certificate issuers per environment
- Set reasonable certificate renewal windows
- Monitor certificate expiration dates
- Store private keys as Sealed Secrets

## Monitoring and Auditing
- Enable Kubernetes audit logging
- Monitor for suspicious pod behavior
- Alert on privilege escalation attempts
- Track secret access patterns
- Log all administrative actions
- Implement security event correlation

## Supply Chain Security
- Verify Helm chart signatures when available
- Pin Flux component versions explicitly
- Review third-party chart dependencies
- Scan infrastructure manifests for misconfigurations
- Use policy engines (OPA, Kyverno) for admission control
- Implement automated security scanning in CI/CD

## Incident Response
- Document security incident procedures
- Maintain secure backup of sealed secrets private key
- Implement automated secret rotation on breach
- Have cluster disaster recovery plan
- Test security incident response regularly

## Compliance
- Document data sensitivity classifications
- Implement required compliance controls
- Audit configurations against security benchmarks
- Maintain change logs for compliance reporting
- Review security posture quarterly
