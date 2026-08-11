# Flux Web UI with tsidp OIDC

## Purpose

This runbook exposes the Flux Operator Web UI only at:

```text
https://flux.${PRIVATE_DOMAIN}
```

Traefik terminates TLS with the `flux-web-tls` Certificate. Flux Operator serves HTTP only to the in-cluster Ingress backend on `Service/flux-operator` port `http-web` (`9080`). Browser users authenticate with the in-cluster `tsidp` issuer; Flux then impersonates their mapped Kubernetes group and Kubernetes RBAC remains the authorization authority.

The initial access level is read-only. Never bind a user or group to `flux-web-admin` as part of this rollout.

## Current GitOps prerequisites

The following resources are already reconciled before enabling the UI:

- `Certificate/flux-web-tls` in `flux-system` writes TLS material to `Secret/flux-web-tls`.
- ExternalDNS watches both `Service` and `Ingress` resources, remains restricted to `${PRIVATE_DOMAIN}`, and publishes private targets without Cloudflare proxying.
- `ClusterRole/flux-web-readonly` and its binding extend the existing `tsidp:viewer` access only with cluster-scoped namespace and `FluxInstance` discovery. The existing `view` binding grants namespaced read access and denies Secrets and mutation verbs.
- The narrow CoreDNS rewrite and Tailscale egress Service allow cluster workloads, including Flux Operator, to retrieve tsidp OIDC discovery and JWKS through `idp.${ts_net}` without committing the private tailnet hostname.

Keep `web.enabled: false` until the dedicated client described below exists as a SealedSecret. Enabling the UI without OAuth2 configuration would expose an unauthenticated endpoint.

## 1. Register a dedicated tsidp client

In the tsidp administration UI, register a new confidential client exclusively for Flux Web UI. Do not reuse the Headlamp client, the former kubelogin test client, or `TS_AUTHKEY` used by the tsidp Pod.

| Field | Required value |
| --- | --- |
| Client name | `flux-web` or an equivalent descriptive name |
| Redirect URI | `https://flux.${PRIVATE_DOMAIN}/oauth2/callback` |
| Grant | Authorization Code |
| Allowed scopes/claims | `openid`, `email`, `profile`; tsidp supports only these standard scopes. The Flux Web config explicitly overrides Flux's broader default scope set. |

Record the client ID and client secret only in a trusted local secret manager. The client secret is shown once; do not paste it into chat, shell history, Git, or a plaintext Kubernetes Secret.

Authorized tsidp users must receive the raw `groups: ["viewer"]` claim. Flux maps that claim to `tsidp:viewer` before Kubernetes impersonation, matching the existing RBAC subject.

## 2. Create the Flux client SealedSecret

Create a strictly namespaced SealedSecret at:

```text
infrastructure/controllers/flux-operator/flux-web-client-sealed-secret.yaml
```

It must decrypt to `Secret/flux-web-client` in `flux-system` with exactly these keys:

```text
client-id
client-secret
issuer-url
```

Use the repository rotation script from a trusted terminal:

```bash
sh scripts/rotate-oidc-sealed-secrets.sh
```

Every prompt is optional, so press Enter to preserve an existing encrypted value when rotating only one credential. The script prompts without echoing client secrets, uses the repository Sealed Secrets public certificate, and updates only the supplied keys in this manifest and/or Headlamp's OIDC SealedSecret. Plaintext is never written to Git and is removed from its protected temporary directory immediately after sealing.

Before committing, inspect only metadata and encrypted structure; do not decode the SealedSecret:

```bash
kubectl create --dry-run=client \
  -f infrastructure/controllers/flux-operator/flux-web-client-sealed-secret.yaml \
  -o jsonpath='{.metadata.namespace}/{.metadata.name}{"\n"}'
```

Expected output:

```text
flux-system/flux-web-client
```

## 3. Enable the UI after the sealed client exists

Add the SealedSecret to `infrastructure/controllers/flux-operator/kustomization.yaml`, then update `release.yaml` in the same reviewed commit. The required shape is:

```yaml
spec:
  valuesFrom:
    - kind: Secret
      name: flux-web-client
      valuesKey: client-id
      targetPath: web.config.authentication.oauth2.clientID
    - kind: Secret
      name: flux-web-client
      valuesKey: client-secret
      targetPath: web.config.authentication.oauth2.clientSecret
    - kind: Secret
      name: flux-web-client
      valuesKey: issuer-url
      targetPath: web.config.authentication.oauth2.issuerURL
  values:
    web:
      enabled: true
      userActions:
        access: Impersonated
      config:
        baseURL: https://flux.${PRIVATE_DOMAIN}
        authentication:
          type: OAuth2
          sessionDuration: 8h
          oauth2:
            provider: OIDC
            # tsidp rejects Flux's default offline_access and groups scopes.
            scopes:
              - openid
              - email
              - profile
            validations:
              - expression: "claims.groups.exists(g, g == 'viewer')"
                message: "user must belong to the viewer group"
            impersonation:
              username: "claims.email"
              groups: "claims.groups.map(g, 'tsidp:' + g)"
      ingress:
        enabled: true
        className: traefik
        annotations:
          external-dns.alpha.kubernetes.io/hostname: flux.${PRIVATE_DOMAIN}
        hosts:
          - host: flux.${PRIVATE_DOMAIN}
            paths:
              - path: /
                pathType: Prefix
        tls:
          - secretName: flux-web-tls
            hosts:
              - flux.${PRIVATE_DOMAIN}
```

Set `oauth2.scopes` exactly as shown: without this override, Flux Operator v0.57.0 requests `offline_access` and `groups`, which tsidp rejects with `invalid_scope`. tsidp injects the `groups` claim through its configured capability rules rather than through an OAuth scope.

The group transformation is mandatory: tsidp emits `viewer`, while the existing Kubernetes binding is to `tsidp:viewer`. Do not change the global `tsidp-viewer` binding merely to compensate for an incorrect Flux claim mapping.

`Impersonated` is retained so any action would be authorized as the end user. The rollout grants no custom action verbs and no `flux-web-admin` binding, so mutating actions remain unavailable or denied.

## 4. Reconcile and validate

Render and dry-run before pushing:

```bash
kustomize build infrastructure/controllers
kustomize build infrastructure/configs
kubectl apply --server-side --dry-run=server \
  -k infrastructure/controllers/flux-operator
flux build kustomization infra-controllers --path clusters/kyrion
flux build kustomization infra-configs --path clusters/kyrion
git diff --check
```

After GitOps reconciliation:

```bash
flux reconcile kustomization infra-controllers -n flux-system --with-source
flux reconcile helmrelease flux-operator -n flux-system --with-source

flux get helmrelease flux-operator -n flux-system
kubectl -n flux-system get deployment,service,ingress,certificate,secret flux-operator flux-web-tls
kubectl -n flux-system describe ingress flux-operator
```

From a Tailnet browser, verify this sequence:

1. `https://flux.${PRIVATE_DOMAIN}` redirects to tsidp.
2. The authorization-code callback returns to `/oauth2/callback` without a redirect loop.
3. The Flux dashboard loads and is restricted to the RBAC-visible namespaces.
4. Resource and workload reads work, while Secret reads are unavailable.
5. Reconcile, suspend/resume, restart, delete, artifact download, and other mutating actions are absent or denied.

Verify the authorization boundary independently before and after browser testing:

```bash
kubectl auth can-i list fluxinstances.fluxcd.controlplane.io \
  --as='tsidp:smoke-test' --as-group='tsidp:viewer'
kubectl auth can-i get secrets --all-namespaces \
  --as='tsidp:smoke-test' --as-group='tsidp:viewer'
kubectl auth can-i patch kustomizations.kustomize.toolkit.fluxcd.io --all-namespaces \
  --as='tsidp:smoke-test' --as-group='tsidp:viewer'
```

Expected results: `yes`, `no`, `no`.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Redirect loop or callback rejection | Confirm the registered URI is exactly `/oauth2/callback`, `baseURL` exactly matches the browser hostname, and the issuer URL in the SealedSecret equals OIDC discovery `issuer`. |
| UI reports OIDC discovery/JWKS failure | Confirm `Service/tsidp-egress` is Ready, CoreDNS has the exact issuer rewrite, and query discovery from the `flux-system` namespace. |
| Login works but UI is empty or says limited access | Verify the token has raw `groups: ["viewer"]`, the Flux mapping prefixes it to `tsidp:viewer`, and `tsidp-viewer` plus `flux-web-readonly` bindings exist. |
| UI can read sensitive data or actions appear | Remove the applicable RBAC binding immediately. Check that no group is bound to `flux-web-admin` and that the user has no unrelated broad RBAC grants. |
| DNS/TLS failure | Check `Certificate/flux-web-tls`, Ingress status, ExternalDNS logs, and that `flux.${PRIVATE_DOMAIN}` resolves to Traefik’s private load-balancer address. |

## Rollback

1. Remove or revoke the tsidp client if its secret is exposed; create a replacement client before re-enabling the UI.
2. Revert the UI-enable commit so `web.enabled: false`; reconcile `HelmRelease/flux-operator`.
3. If immediate access removal is necessary, remove the Ingress/DNS record or the `flux-web-readonly` binding first.
4. Keep `Certificate/flux-web-tls`, the tsidp PVC, and tsidp’s own `TS_AUTHKEY` untouched unless there is a separate credential-compromise reason.

## Related documentation

- [tsidp OIDC for Headlamp](tsidp-sso.md)
- [Flux Operator migration](flux-operator-migration.md)
- [Secret Management](../security/secret-management.md)
- [Flux Web UI SSO guide](https://fluxoperator.dev/docs/web-ui/sso-dex/)
- [Flux Web UI configuration reference](https://fluxoperator.dev/docs/web-ui/web-config-api/)
