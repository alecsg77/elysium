## Create LibreChar credentials env sealed secret

```shell
kubectl create secret generic librechat-credentials-env -n ai --from-env-file=apps/base/ai/librechat-credentials.env --dry-run=client -o yaml | kubeseal -o yaml > apps/base/ai/librechat-credentials-env-sealed-secret.yaml
```

## Create Open-WebUI credentials env sealed secret

```shell
kubectl create secret generic openwebui-credentials-env -n ai --from-env-file=apps/base/ai/openwebui-credentials.env --dry-run=client -o yaml | kubeseal -o yaml > apps/base/ai/openwebui-credentials-env-sealed-secret.yaml
```

## Create searxng config

```shell
kubectl create secret generic searxng-config -n ai --from-file=settings.yml=apps/base/ai/searxng-config.yaml --dry-run=client -o yaml | kubeseal -o yaml > apps/base/ai/searxng-config-sealed-secret.yaml
```

## LangFlow

LangFlow is a visual framework for building multi-agent and RAG applications. It is deployed with:

- **PostgreSQL Database**: Integrated PostgreSQL via langflow-ide chart dependency (Bitnami PostgreSQL chart)
- **LangFlow Application**: Official langflow-ide Helm chart from langflow-ai
- **Access**: Available via Tailscale at `https://langflow.<ts_net>`
- **Auto-login**: Disabled by default in chart; enable via kyrion overlay using `backend.autoLogin` value

### Configuration

The deployment uses the official [LangFlow Helm chart](https://github.com/langflow-ai/langflow-helm-charts) with integrated PostgreSQL:

- **Helm Chart**: `langflow-ide` from `https://langflow-ai.github.io/langflow-helm-charts`
- **PostgreSQL**: Enabled as chart dependency with `fullnameOverride: langflow-postgresql`
- **Database**: `langflow` database with user `langflow`
- **Storage**: PostgreSQL uses 10Gi persistent volume on local-path storage class
- **Backend Port**: 7860 (backend-only mode)
- **Frontend Port**: 8080 (separate frontend service)

### Security Note

Default PostgreSQL credentials are `langflow/langflow`. For production, seal the PostgreSQL credentials:

```shell
kubectl create secret generic langflow-postgresql-secret -n ai \
  --from-literal=postgres-password=$(openssl rand -base64 32) \
  --from-literal=password=$(openssl rand -base64 32) \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml > apps/base/ai/langflow-postgresql-sealed-secret.yaml
```

Then update the PostgreSQL configuration in `langflow.yaml`:
```yaml
# In the HelmRelease values.postgresql section
postgresql:
  enabled: true
  fullnameOverride: "langflow-postgresql"
  auth:
    username: "langflow"
    database: "langflow"
    existingSecret: "langflow-postgresql-secret"
```

The Bitnami PostgreSQL chart expects these keys in the secret:
- `postgres-password`: PostgreSQL admin password
- `password`: User password

### Enabling Auto-Login

Auto-login is disabled by default for security. To enable it for homelab/dev environments, create an overlay in `apps/kyrion/`:

```yaml
# apps/kyrion/langflow-patch.yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: langflow
  namespace: ai
spec:
  values:
    langflow:
      backend:
        autoLogin: true
```
