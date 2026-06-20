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

## OpenClaw

`apps/base/ai/openclaw.yaml` contains the base application definition only: the
upstream `GitRepository` for `openclaw/openclaw`.

The actual installation and cluster-specific configuration live in the kyrion
overlay:

- `apps/kyrion/openclaw.yaml` for the Flux `Kustomization` and Tailscale Ingress
- `apps/kyrion/openclaw-sealed-secret.yaml` for the gateway token
- `apps/kyrion/openclaw-copilot-auth-secret.yaml` for Copilot auth wiring

### Why this uses cluster Tailscale ingress

This deployment intentionally uses the cluster's `Ingress` with
`ingressClassName: tailscale` instead of OpenClaw's native
`gateway.tailscale.mode = "serve"` support.

The upstream Tailscale integration expects the `tailscale` CLI and a logged-in
local `tailscaled` daemon on the same runtime as OpenClaw so it can manage
`tailscale serve` and verify identity headers via `tailscale whois`.

In this repository, private access is already standardized through the
Kubernetes Tailscale operator and Ingress resources, so the OpenClaw pod is
exposed through that cluster-native path rather than trying to run a separate
local Tailscale daemon inside the workload.

### Gateway token secret

Generate or rotate the gateway token with a sealed secret named
`openclaw-secrets`:

```shell
kubectl create secret generic openclaw-secrets -n ai \
  --from-literal=OPENCLAW_GATEWAY_TOKEN="$(openssl rand -hex 32)" \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml > apps/kyrion/openclaw-sealed-secret.yaml
```

### GitHub Copilot auth secret

The deployment is pre-wired to read either `COPILOT_GITHUB_TOKEN` or `GH_TOKEN`
from a secret named `openclaw-copilot-auth`. Replace
`apps/kyrion/openclaw-copilot-auth-secret.yaml` with a sealed secret before
expecting Copilot-backed requests to work.

The token must be a Copilot-capable GitHub OAuth credential, not just a generic
personal access token.

```shell
kubectl create secret generic openclaw-copilot-auth -n ai \
  --from-literal=COPILOT_GITHUB_TOKEN="$COPILOT_GITHUB_TOKEN" \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem -o yaml > apps/kyrion/openclaw-copilot-auth-secret.yaml
```

OpenClaw is configured to default to `github-copilot/gpt-5.5` once that secret
is populated.
