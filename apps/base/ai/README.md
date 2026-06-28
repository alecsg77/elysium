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
