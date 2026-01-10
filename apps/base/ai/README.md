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

- **PostgreSQL Database**: Bitnami PostgreSQL chart for persistent data storage
- **LangFlow Application**: Official langflow-ide Helm chart from langflow-ai
- **Persistent Storage**: Separate volumes for flows (5Gi), data (10Gi), and PostgreSQL (10Gi)
- **Access**: Available via Tailscale at `https://langflow.<ts_net>`
- **Auto-login**: Disabled by default for security (enable via environment overlay for homelab/dev)

### Configuration

The deployment uses the official [LangFlow Helm chart](https://github.com/langflow-ai/langflow-helm-charts) with PostgreSQL backend:

- **Helm Chart**: `langflow-ide` from `https://langflow-ai.github.io/langflow-helm-charts`
- **Database URL**: `postgresql://langflow:langflow@langflow-postgresql:5432/langflow`
- **Config Directory**: `/app/data` (persistent volume mounted)
- **Backend Port**: 7860 (backend-only mode)
- **Frontend Port**: 8080 (separate frontend service)
- **Resources**: Backend 500m-2 CPU, 1-4Gi memory; Frontend 300m-1 CPU, 512Mi-1Gi memory

### Security Note

Default PostgreSQL credentials are `langflow/langflow`. For production, create a sealed secret with secure credentials that match the Bitnami PostgreSQL chart expectations:

```shell
kubectl create secret generic langflow-postgresql-secret -n ai \
  --from-literal=postgres-password=$(openssl rand -base64 32) \
  --from-literal=password=$(openssl rand -base64 32) \
  --from-literal=username=langflow \
  --from-literal=database=langflow \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml > apps/base/ai/langflow-postgresql-sealed-secret.yaml
```

Then update the PostgreSQL HelmRelease in `langflow.yaml` to use the sealed secret:
```yaml
# In the langflow-postgresql HelmRelease values
auth:
  existingSecret: "langflow-postgresql-secret"
```

Note: When using `existingSecret`, the Bitnami PostgreSQL chart expects these keys:
- `postgres-password`: PostgreSQL admin password
- `password`: User password
- `username`: Database username (optional if specified in values)
- `database`: Database name (optional if specified in values)
