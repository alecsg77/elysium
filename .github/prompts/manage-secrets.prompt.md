---
mode: 'agent'
model: Claude Sonnet 4
tools: ['codebase']
description: 'Create or rotate sealed secrets securely'
---

# Manage Sealed Secrets

You are helping create and manage encrypted secrets for the Elysium Kubernetes homelab using Bitnami Sealed Secrets.

## Prerequisites

- Access to the cluster (kubeconfig configured)
- `kubeseal` CLI installed
- Cluster public key available at `etc/certs/pub-sealed-secrets.pem`

## Creating New Sealed Secrets

### Step 1: Gather Secret Information

Ask the user for:
1. **Secret name** (kebab-case)
2. **Namespace** where secret will be used
3. **Secret type**: generic, docker-registry, tls, opaque
4. **Secret keys and values** (will be encrypted)

### Step 2: Create Sealed Secret

**For generic secrets:**
```bash
kubectl create secret generic <secret-name> \
  --from-literal=key1=value1 \
  --from-literal=key2=value2 \
  --namespace=<namespace> \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > apps/base/<app>/<secret-name>-sealed-secret.yaml
```

**For secrets from files:**
```bash
kubectl create secret generic <secret-name> \
  --from-file=config=/path/to/config \
  --namespace=<namespace> \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > apps/base/<app>/<secret-name>-sealed-secret.yaml
```

**For secrets from stdin:**
```bash
echo -n "secret-value" | kubectl create secret generic <secret-name> \
  --dry-run=client --from-file=key=/dev/stdin \
  --namespace=<namespace> -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > apps/base/<app>/<secret-name>-sealed-secret.yaml
```

**For Docker registry secrets:**
```bash
kubectl create secret docker-registry <secret-name> \
  --docker-server=<registry> \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email> \
  --namespace=<namespace> \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > apps/base/<app>/<secret-name>-sealed-secret.yaml
```

**For TLS secrets:**
```bash
kubectl create secret tls <secret-name> \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem \
  --namespace=<namespace> \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > apps/base/<app>/<secret-name>-sealed-secret.yaml
```

### Step 3: Add to Kustomization

Update `apps/base/<app>/kustomization.yaml`:
```yaml
resources:
  - namespace.yaml
  - <secret-name>-sealed-secret.yaml
  - release.yaml
```

### Step 4: Reference in Application

**In HelmRelease:**
```yaml
spec:
  valuesFrom:
    - kind: Secret
      name: <secret-name>
      valuesKey: values.yaml
```

**As environment variable:**
```yaml
env:
  - name: API_KEY
    valueFrom:
      secretKeyRef:
        name: <secret-name>
        key: api-key
```

**As volume mount:**
```yaml
volumes:
  - name: secret-volume
    secret:
      secretName: <secret-name>
volumeMounts:
  - name: secret-volume
    mountPath: /etc/secrets
    readOnly: true
```

## Rotating Secrets

### Step 1: Create New Sealed Secret
Follow the creation steps above with the new secret value.

### Step 2: Update Reference
Commit the new sealed secret file to Git.

### Step 3: Verify Deployment
```bash
# Check sealed secret unsealed correctly
kubectl get secret <secret-name> -n <namespace>

# Verify application picked up new secret
kubectl rollout status deployment/<app> -n <namespace>

# Restart pods if needed
kubectl rollout restart deployment/<app> -n <namespace>
```

## Cluster-Wide Secrets

For cluster-wide secrets (used in Flux substitution):

### Step 1: Add to Cluster Sealed Secrets
Edit `clusters/kyrion/sealed-secrets.yaml` and add the new key-value pair.

### Step 2: Update Sealed Secret
```bash
# Get current sealed secret
kubectl get sealedsecret cluster-secret-vars -n flux-system -o yaml > temp-secret.yaml

# Edit to add new keys
# Re-seal and update the file
```

### Step 3: Reference in Kustomization
Use `${VARIABLE_NAME}` syntax in manifests that reference cluster-secret-vars via `postBuild.substituteFrom`.

## Security Best Practices

- **NEVER** commit plain text secrets to Git
- **ALWAYS** use kubeseal to encrypt before committing
- Delete plain text secret files after sealing
- Rotate secrets regularly (quarterly recommended)
- Use unique secrets per environment
- Limit secret access with RBAC
- Audit secret usage in applications
- Back up the sealed-secrets private key securely (stored in cluster)

## Troubleshooting

### Sealed Secret Not Decrypting
```bash
# Check sealed-secrets controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=sealed-secrets

# Verify sealed secret exists
kubectl get sealedsecret <name> -n <namespace>

# Check if secret was created
kubectl get secret <name> -n <namespace>
```

### Wrong Namespace
Sealed secrets are namespace-scoped by default. If the namespace changes, you must recreate the sealed secret.

### Key Not Found
Verify the key name in the sealed secret matches the key referenced in the application.

### Certificate Issues
Ensure you're using the correct public certificate from `etc/certs/pub-sealed-secrets.pem`.

## Validation

After creating a sealed secret:
1. Commit to Git
2. Let Flux reconcile or force: `flux reconcile kustomization apps`
3. Verify secret exists: `kubectl get secret <name> -n <namespace>`
4. Check secret contents: `kubectl get secret <name> -n <namespace> -o yaml`
5. Verify application can access secret

Refer to [Security guidelines](../.github/instructions/security.instructions.md#secret-management) for more details.
