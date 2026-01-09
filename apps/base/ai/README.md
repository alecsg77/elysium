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
- **LangFlow Application**: Official langflowai/langflow image via onechart
- **Persistent Storage**: 10Gi volumes for both PostgreSQL data and LangFlow configuration
- **Access**: Available via Tailscale at `https://langflow.<ts_net>`
- **Auto-login**: Enabled by default (set `LANGFLOW_AUTO_LOGIN=false` for production)

### Configuration

The deployment follows the official Docker Compose setup from [LangFlow documentation](https://docs.langflow.org/deployment-docker):

- **Database URL**: `postgresql://langflow:langflow@langflow-postgresql:5432/langflow`
- **Config Directory**: `/app/langflow` (persistent volume mounted)
- **Port**: 7860
- **Resources**: 500m-2 CPU, 1-4Gi memory

### Security Note

Default PostgreSQL credentials are `langflow/langflow`. For production, create a sealed secret with secure credentials:

```shell
kubectl create secret generic langflow-postgresql-secret -n ai \
  --from-literal=postgres-password=<secure-password> \
  --from-literal=password=<secure-password> \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml > apps/base/ai/langflow-postgresql-sealed-secret.yaml
```

Then update `langflow-postgresql.yaml` to use the sealed secret:
```yaml
auth:
  existingSecret: "langflow-postgresql-secret"
```
