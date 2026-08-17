# Secret Management Guide

Complete guide for managing secrets in the Elysium Kubernetes cluster using Bitnami Sealed Secrets.

## ⚠️ CRITICAL SECURITY RULES

- **NEVER** commit plain text secrets to the repository
- **ALWAYS** use Sealed Secrets for sensitive data
- **VERIFY** secrets are encrypted before committing
- **ROTATE** secrets after compromise or when their operational lifecycle requires it
- **AUDIT** secret access in application logs

## Secret Types

| Type | Location | Purpose | Reference Method |
|------|----------|---------|------------------|
| **Cluster-wide** | `clusters/kyrion/sealed-secrets.yaml` | Cluster variables, tokens | `postBuild.substituteFrom` |
| **App-specific** | `apps/base/<app>/*-sealed-secret.yaml` | App credentials, API keys | `valuesFrom` in HelmRelease |
| **ConfigMaps** | `clusters/kyrion/config-map.yaml` | Non-sensitive config | `postBuild.substituteFrom` |

## Sealed Secret Creation Workflow

### Prerequisites

- `kubeseal` CLI installed
- Access to cluster via `kubectl`
- Public key file: `etc/certs/pub-sealed-secrets.pem`

### Creating a Sealed Secret

#### Generic Secret

```bash
# Create sealed secret from literal value
echo -n "secret-value" | kubectl create secret generic app-secret \
  --namespace=<namespace> \
  --dry-run=client --from-file=key=/dev/stdin -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > sealed-secret.yaml
```

#### From File

```bash
# Create sealed secret from file
kubectl create secret generic app-config \
  --namespace=<namespace> \
  --from-file=config.yaml \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > sealed-secret.yaml
```

#### Docker Registry Credentials

```bash
# Create sealed secret for Docker registry
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com \
  --docker-username=user \
  --docker-password=pass \
  --namespace=<namespace> \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > sealed-secret.yaml
```

#### Multiple Keys

```bash
# Create sealed secret with multiple keys
kubectl create secret generic app-secret \
  --namespace=<namespace> \
  --from-literal=username=admin \
  --from-literal=password=secret123 \
  --from-file=config.json \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > sealed-secret.yaml
```

## Variable Substitution

Flux supports variable substitution in manifests using `postBuild.substituteFrom`:

### Syntax

Use `${VARIABLE_NAME}` in manifests:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  api_url: ${API_URL}
  timeout: ${TIMEOUT}
```

### Reference in Kustomization

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: apps
  namespace: flux-system
spec:
  postBuild:
    substituteFrom:
      - kind: ConfigMap
        name: cluster-vars
      - kind: Secret
        name: cluster-secret-vars
```

### Security Model

- **Public key encryption**: Allows safe commits to Git
- **Cluster-side decryption**: Only cluster can decrypt
- **Namespace-scoped**: Secrets bound to specific namespace

## Secret Reference Patterns

### In HelmRelease (valuesFrom)

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: myapp
  namespace: myapp
spec:
  valuesFrom:
    - kind: Secret
      name: app-secret
      valuesKey: values.yaml
```

### In Pod (Environment Variable)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: app
    env:
    - name: API_KEY
      valueFrom:
        secretKeyRef:
          name: app-secret
          key: api-key
```

### In Pod (Volume Mount)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: app
    volumeMounts:
    - name: secrets
      mountPath: /etc/secrets
      readOnly: true
  volumes:
  - name: secrets
    secret:
      secretName: app-secret
```

### In Kustomization (Variable Substitution)

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: apps
spec:
  postBuild:
    substituteFrom:
      - kind: Secret
        name: cluster-secret-vars
```

## Sealed Secrets Key Management

### Key Location

- **Public Key**: `etc/certs/pub-sealed-secrets.pem` (safe to commit to Git)
- **Private Keys**: Stored in controller-managed cluster Secrets; retain an off-cluster recovery bundle and never commit it to Git

### Backup Procedure

Back up every active sealing-key Secret, not only the newest key. Export only to
a controlled temporary directory and move the resulting bundle to protected
off-cluster storage. Encrypt it when that storage is not already encrypted, and
remove the temporary plaintext after verifying the retained artifact. Never put
the bundle, its location, or access details in Git.

```bash
set -euo pipefail
umask 077
tmpdir="$(mktemp -d)"
trap 'rm -rf -- "$tmpdir"' EXIT

# The plaintext exists only inside the mode-0700 temporary directory.
kubectl get secret -n flux-system \
  -l sealedsecrets.bitnami.com/sealed-secrets-key \
  -o yaml > "$tmpdir/sealed-secrets-keys.yaml"

# Example: use the approved off-cluster encryption recipient from the private
# operations record. Do not commit either artifact or recipient details.
age --encrypt --recipient "<approved-recipient>" \
  --output "$tmpdir/sealed-secrets-keys.yaml.age" \
  "$tmpdir/sealed-secrets-keys.yaml"

# Verify decryptability with an authorized custodian before storing the encrypted
# artifact in the approved off-cluster location.
age --decrypt --identity "<authorized-identity>" \
  "$tmpdir/sealed-secrets-keys.yaml.age" >/dev/null
```

The `age` commands are an example for unencrypted destination storage. They are
unnecessary when the retained artifact is placed directly on adequately
protected encrypted media.

**CRITICAL**: The sealing-key set is required to decrypt the corresponding
SealedSecret resources. Loss of every applicable key means permanent loss of
those encrypted secret values.

### Recovery Procedure (Disaster Recovery)

```bash
# Restore the complete sealing-key set before starting the controller
kubectl apply -f sealed-secrets-keys.yaml

# Restart sealed-secrets controller to load key
kubectl rollout restart deployment -n flux-system sealed-secrets-controller

# Verify unsealing works
kubectl get sealedsecrets -A
kubectl get secrets -A | grep sealed
```

### Sealing Key Renewal

The controller renews sealing keys automatically and retains older active keys
so existing SealedSecrets remain decryptable. Recreate the off-cluster key
backup after adopting a newly issued public certificate or re-encrypting
SealedSecrets. Periodic renewal does not rotate the underlying application
passwords.

Manual renewal is an advanced operation and is not part of the homelab baseline:

```bash
# Generate new key pair
kubectl create secret tls sealed-secrets-new-key \
  --cert=new-cert.pem \
  --key=new-key.pem \
  -n flux-system

# Sealed-secrets controller automatically picks up new key
# Old key remains for decrypting existing secrets
# Re-seal all secrets with new key over time
```

### Security Considerations

- **NEVER** commit unsealed secrets or the private key to Git
- **Store backups on protected offline media**, encrypting them when the media is not already encrypted
- **Test recovery** after creating or replacing the retained key backup
- **Document key custodians** who have access to backups
- **Use separate keys per cluster** in multi-cluster environments

## Troubleshooting

### Secret Not Decrypted

**Symptoms**: SealedSecret exists but Secret not created

**Resolution**:
1. Check sealed-secrets controller logs:
   ```bash
   kubectl logs -n flux-system deploy/sealed-secrets-controller
   ```
2. Verify SealedSecret status:
   ```bash
   kubectl describe sealedsecret <name> -n <namespace>
   ```
3. Check if namespace exists (SealedSecrets are namespace-scoped)

### Wrong Namespace

**Symptoms**: Secret not available in expected namespace

**Resolution**:
1. Recreate SealedSecret with correct namespace
2. SealedSecrets are encrypted for specific namespace - cannot be moved

### Variable Not Substituted

**Symptoms**: `${VARIABLE_NAME}` appears literally in deployed resources

**Resolution**:
1. Verify ConfigMap/Secret exists:
   ```bash
   kubectl get cm,secret -n flux-system
   ```
2. Check key name matches exactly (case-sensitive)
3. Verify Kustomization has `postBuild.substituteFrom` reference

### Permission Denied

**Symptoms**: Pod cannot read Secret

**Resolution**:
1. Check RBAC for ServiceAccount
2. Verify ServiceAccount is correct in Pod spec
3. Check Secret exists in same namespace as Pod

## Best Practices

### Development

✅ **Do**:
- Create SealedSecrets in same namespace as consumers
- Use descriptive names for keys
- Add README documenting what secrets are for (not values)
- Test locally before committing
- Use `.gitignore` to prevent accidental commits of unsealed secrets

❌ **Don't**:
- Commit plain text secrets
- Reuse credentials across namespaces without an explicitly accepted tradeoff
- Store private keys in Git
- Share SealedSecret files between clusters

### Operations

✅ **Do**:
- Refresh the sealing-key backup after adopting a new certificate
- Rotate application secrets after compromise or when their lifecycle requires it
- Monitor sealed-secrets controller health
- Document secret ownership and rotation schedule
- Audit secret access in application logs

❌ **Don't**:
- Skip backups (key loss = permanent secret loss)
- Use same encryption key across clusters
- Delay rotation after suspected compromise
- Store key backups on unprotected media

### Security

✅ **Do**:
- Use protected offline storage for key backups
- Encrypt key backups when the destination is not already encrypted
- Limit access to private key backups
- Test recovery after replacing the retained key backup
- Rotate after team member changes

❌ **Don't**:
- Share private keys via email/Slack
- Store backups on public cloud without encryption
- Use weak encryption for backups
- Skip testing recovery procedure

## Guided Workflows

For interactive guidance, use the Copilot skill:
```
Use the manage-sealed-secrets skill to guide secret creation
```

## Related Documentation

- [Repository Structure Standards](/docs/standards/repository-structure.md)
- [Application Deployment](/docs/runbooks/add-application.md)
- [Cluster Architecture](/docs/architecture/cluster-architecture.md)
- [Secure Troubleshooting](/docs/security/secure-troubleshooting.md)

## External References

- [Bitnami Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
- [Flux Variable Substitution](https://fluxcd.io/flux/components/kustomize/kustomization/#variable-substitution)
