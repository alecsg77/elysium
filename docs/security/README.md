# Security

Security best practices and procedures for the Elysium Kubernetes cluster.

## Contents

- **[Secret Management Guide](secret-management.md)** - Complete guide for Bitnami Sealed Secrets:
  - Critical security rules
  - Secret types and locations
  - Sealed Secret creation workflow (generic, from file, Docker registry, multiple keys)
  - Variable substitution patterns
  - Secret reference patterns (HelmRelease, Pod, Kustomization)
  - Key backup and recovery procedures
  - Key rotation procedures
  - Troubleshooting (decryption, namespace, substitution, permissions)
  - Best practices for development, operations, and security

- **[Secure Troubleshooting](secure-troubleshooting.md)** - Guidelines for handling sensitive information:
  - Core principle: treat all artifacts as sensitive
  - Mandatory pre-share steps and redaction guidelines
  - Security scan procedures (ripgrep and grep)
  - Redaction workflow (collect, scan, redact, verify, share)
  - Post-incident review checklist
  - Safe diagnostic commands
  - Redaction examples (logs, values, events)
  - Emergency response procedures

## Quick Reference

### Creating Sealed Secrets

```bash
# Generic secret
echo -n "secret-value" | kubectl create secret generic app-secret \
  --namespace=<namespace> \
  --dry-run=client --from-file=key=/dev/stdin -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > sealed-secret.yaml
```

### Security Scan

```bash
# Scan diagnostics for sensitive data
rg -n 'password|secret|token|apikey|bearer' diagnostics/
```

### Key Backup

```bash
# Backup sealed-secrets key (quarterly)
kubectl get secret -n sealed-secrets-system sealed-secrets-key -o yaml > sealed-secrets-backup.yaml
```

## Security Principles

### Secrets
- **Never** commit plain text secrets to Git
- **Always** use Sealed Secrets for sensitive data
- **Verify** secrets are encrypted before committing
- **Rotate** secrets regularly (quarterly recommended)
- **Backup** sealed-secrets key quarterly

### Troubleshooting
- **Treat** all artifacts as sensitive until proven otherwise
- **Redact** secrets, tokens, IPs, hostnames before sharing
- **Scan** diagnostics with automated tools before posting
- **Document** every redaction for future responders
- **Rotate** credentials immediately if exposure suspected

### RBAC
- **Namespace isolation**: Dedicated ServiceAccounts per app
- **Least privilege**: Grant only required permissions
- **Cluster-admin**: Reserved for infrastructure only

### Network
- **Default deny**: Network policies where applicable
- **Explicit allow**: Only required communication paths
- **Private ingress**: Use Tailscale for internal services

## Related Documentation

- [Cluster Architecture](/docs/architecture/cluster-architecture.md)
- [Repository Structure Standards](/docs/standards/repository-structure.md)
- [Application Deployment](/docs/runbooks/add-application.md)
- [Web-Based Troubleshooting](/docs/troubleshooting/web-troubleshooting.md)

