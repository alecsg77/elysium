# tsidp OIDC for Headlamp

This runbook configures per-user OIDC authentication for Headlamp through the private `tsidp` issuer and keeps Kubernetes authorization per user through the `tsidp:viewer` RBAC group.

## Architecture decision

There are two deliberate identity paths in this cluster. Do not merge them accidentally.

```text
kubectl from a Tailnet device
  -> Tailscale Kubernetes API proxy (auth mode)
  -> Tailscale identity impersonation
  -> Kubernetes RBAC

Headlamp browser login
  -> tsidp authorization-code flow
  -> Headlamp forwards the personal ID token to the in-cluster API server
  -> k3s validates tsidp JWT
  -> Kubernetes RBAC
```

| Use case | Authoritative identity | Required configuration |
| --- | --- | --- |
| Human `kubectl` access through the Tailnet | Tailscale identity and Tailscale Kubernetes API-proxy auth mode | Keep `apiServerProxyConfig.mode: "true"`; do **not** use `kubelogin` or switch the proxy to `noauth`. |
| Headlamp login and authorization | `tsidp` OIDC identity | k3s `AuthenticationConfiguration`, a Headlamp OIDC client, and `tsidp:viewer` RBAC. |
| Other OIDC-capable applications | `tsidp` OIDC identity | App-specific OIDC client and application configuration. k3s configuration is not needed unless the app forwards user tokens to Kubernetes. |

The `ClusterRoleBinding/tsidp-viewer` remains intentional. It grants the OIDC group `tsidp:viewer` the Kubernetes built-in `view` ClusterRole, which provides namespace-scoped read-only access without Secret reads or write permissions.

## Current state and guardrails

- Keep the Tailscale API server proxy in auth mode:

  ```yaml
  apiServerProxyConfig:
    mode: "true"
  ```

  Changing this to `noauth` would deliberately break the existing Tailnet-authenticated `kubectl` path and is not part of the Headlamp rollout.

- Keep the k3s OIDC files already installed on the control-plane host:

  ```text
  /etc/rancher/k3s/authentication/tsidp.yaml
  /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml
  ```

  They are needed so the in-cluster API server can validate the ID token that Headlamp forwards. Do not remove them while preparing Headlamp.

- The earlier `kubelogin` test client and its Windows kubeconfig are not needed for normal `kubectl` access. Remove that local exec credential and rotate its client secret because it was used for testing and should not be reused for Headlamp.

- Do not use Headlamp's in-cluster ServiceAccount as the logged-in user's Kubernetes identity. The intended Headlamp configuration disables that fallback and forwards the personal OIDC identity instead.

## Prerequisites

Before enabling Headlamp OIDC, confirm:

- `HelmRelease/tsidp` is `Ready` and PVC `tsidp-tsidp-data` is `Bound`.
- The control-plane host can retrieve issuer discovery and JWKS from `tsidp`.
- An authorized Tailnet user receives `groups: ["viewer"]` from `tsidp`.
- `ClusterRoleBinding/tsidp-viewer` is reconciled by Flux.
- The Headlamp browser URL is reachable through the Tailnet and uses HTTPS.
- A break-glass administrator credential remains available on the control-plane host.

Use dedicated OIDC clients per application. A client registered for the earlier local `kubelogin` callback cannot be reused for Headlamp because an OIDC provider requires an exact registered redirect URI.

## 1. Create a dedicated Headlamp OIDC client

In the `tsidp` administration UI, create a client specifically for Headlamp.

Use these values:

| Field | Value |
| --- | --- |
| Client name | `headlamp` or an equivalent descriptive name |
| Redirect URI | `https://<private-headlamp-host>/oidc-callback` |
| Scopes | `openid`, `profile`, `email` |
| Grant | Authorization Code with PKCE when the client/chart supports it |

Record the generated `client_id` and `client_secret` locally. Do not paste either value in chat, a shell command line, Git, or a plaintext Kubernetes Secret.

The Headlamp redirect URI must be the public browser URL plus the literal path `/oidc-callback`; it is not the local callback URI previously used for `kubelogin` testing.

## 2. Align k3s OIDC audience with the Headlamp client

The k3s OIDC configuration must accept tokens whose audience is the **Headlamp client ID**, not the retired `kubelogin` test-client ID.

On the control-plane host, first verify the existing configuration and the issuer/JWKS path. Keep an existing administrator session open during this work.

```bash
sudo sed -n '1,120p' /etc/rancher/k3s/authentication/tsidp.yaml
sudo k3s kubectl get --raw='/readyz?verbose'
```

If the `audiences` value is not the Headlamp client ID, replace it. Enter private values interactively so they do not enter shell history:

```bash
read -rp 'OIDC issuer URL: ' IDP_ISSUER
read -rp 'Headlamp OIDC client ID: ' HEADLAMP_CLIENT_ID

curl --fail --silent --show-error \
  "$IDP_ISSUER/.well-known/openid-configuration" \
  | jq '{issuer, jwks_uri}'

JWKS_URI="$(curl --fail --silent --show-error \
  "$IDP_ISSUER/.well-known/openid-configuration" \
  | jq -r '.jwks_uri')"
curl --fail --silent --show-error "$JWKS_URI" | jq '.keys | length'
```

The returned issuer must exactly equal `IDP_ISSUER`, and the JWKS key count must be greater than zero. Then rewrite only the tsidp authentication configuration:

```bash
sudo tee /etc/rancher/k3s/authentication/tsidp.yaml >/dev/null <<EOF_CONFIG
apiVersion: apiserver.config.k8s.io/v1
kind: AuthenticationConfiguration
jwt:
  - issuer:
      url: ${IDP_ISSUER}
      audiences:
        - ${HEADLAMP_CLIENT_ID}
    claimMappings:
      username:
        claim: sub
        prefix: "tsidp:"
      groups:
        claim: groups
        prefix: "tsidp:"
EOF_CONFIG

sudo chown root:root /etc/rancher/k3s/authentication/tsidp.yaml
sudo chmod 0600 /etc/rancher/k3s/authentication/tsidp.yaml
sudo systemctl restart k3s
sudo systemctl is-active --quiet k3s
sudo k3s kubectl get --raw='/readyz?verbose'
```

Do not add legacy `--oidc-*` API-server flags. The existing k3s drop-in must remain the only OIDC API-server configuration:

```yaml
kube-apiserver-arg+:
  - authentication-config=/etc/rancher/k3s/authentication/tsidp.yaml
```

## 3. Keep and verify the viewer binding

Flux already manages this binding in `infrastructure/configs/tsidp-viewer-clusterrolebinding.yaml`:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tsidp-viewer
subjects:
  - kind: Group
    apiGroup: rbac.authorization.k8s.io
    name: tsidp:viewer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: view
```

Verify its reconciliation with the existing administrator credential:

```bash
kubectl get clusterrolebinding tsidp-viewer -o yaml
kubectl auth can-i get pods --all-namespaces \
  --as='tsidp:smoke-test' --as-group='tsidp:viewer'
kubectl auth can-i get secrets --all-namespaces \
  --as='tsidp:smoke-test' --as-group='tsidp:viewer'
```

Expected results are `yes` for Pod reads and `no` for Secret reads.

## 4. Configure Headlamp through GitOps

This is a separate GitOps change under `monitoring/controllers/headlamp/`. It requires three pieces that must be released together:

1. a `SealedSecret` named `headlamp-oidc` in `kube-system`, containing the Headlamp OIDC client values;
2. HelmRelease values that enable Headlamp OIDC and reference that Secret;
3. removal of Headlamp's ServiceAccount-token fallback and its broad in-cluster RBAC binding.

The required intent for the Headlamp values is:

```yaml
config:
  inCluster: true
  unsafeUseServiceAccountToken: false
  oidc:
    callbackURL: https://headlamp.${PRIVATE_DOMAIN}/oidc-callback
    secret:
      create: false
    externalSecret:
      enabled: true
      hasScopes: true
      name: headlamp-oidc
    useAccessToken: false
    usePKCE: true

env:
  - name: OIDC_CALLBACK_URL
    value: https://headlamp.${PRIVATE_DOMAIN}/oidc-callback
  - name: OIDC_USE_PKCE
    value: "true"

automountServiceAccountToken: false

clusterRoleBinding:
  create: false
```

The encrypted `Secret/headlamp-oidc` must be created locally with `kubeseal`; never commit a plaintext Secret. Create it with the chart external-secret keys: `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_ISSUER_URL`, and `OIDC_SCOPES`. Use `profile,email` for scopes; Headlamp always requests mandatory `openid` itself. Before changing the HelmRelease, inspect that chart version's `values.yaml` and schema to verify the external-secret wiring and OIDC options.

Generate this manifest locally with a temporary, untracked helper or the standard Sealed Secrets workflow in [Secret Management](../security/secret-management.md). Do not commit a credential-generation helper: it is intentionally local because it handles the Headlamp client secret.

The resulting strict, namespace-bound manifest belongs at:

```text
monitoring/controllers/headlamp/headlamp-oidc-sealed-secret.yaml
```

Before staging it, validate only its metadata and encrypted structure. Do not decode it or print its contents:

```bash
kubeconform -strict -ignore-missing-schemas \
  monitoring/controllers/headlamp/headlamp-oidc-sealed-secret.yaml
kubectl create --dry-run=client \
  -f monitoring/controllers/headlamp/headlamp-oidc-sealed-secret.yaml \
  -o jsonpath='{.metadata.namespace}/{.metadata.name}{"\n"}'
```

Expected output is `kube-system/headlamp-oidc`.

Do not configure Headlamp OIDC until the k3s `audiences` value in Step 2 is the same Headlamp client ID. A token minted for a different client audience is rejected by the API server even if issuer, signature, and groups are otherwise valid.

## 5. Validate Headlamp per-user RBAC

After Flux reconciles the Headlamp change:

1. Open Headlamp from an authorized Tailnet device.
2. Complete the `tsidp` browser login.
3. Confirm Headlamp can list Pods but cannot view Secrets or perform writes.
4. In Headlamp's Kubernetes identity/debug display, confirm the effective username begins with `tsidp:` and the effective group includes `tsidp:viewer`.
5. From the existing Tailnet-authenticated `kubectl` context, confirm administrator access still works. This validates that Tailscale proxy auth mode was not changed.

If Headlamp authenticates successfully but sees `forbidden` errors, inspect the `tsidp-viewer` binding and verify that the user token includes the raw `groups: ["viewer"]` claim. If Headlamp receives `401 Unauthorized`, verify the issuer URL and that the token audience equals the Headlamp client ID configured in k3s.

## Rollback

### Headlamp-only failure

Revert the Git commit that enabled Headlamp OIDC and reconcile the Headlamp HelmRelease. Keep the k3s OIDC configuration and `tsidp-viewer` binding if another OIDC application will use them; otherwise schedule their removal as a separate, deliberate cleanup.

### k3s API-server failure

Keep the break-glass administrator session open. Remove only the structured OIDC configuration and restart k3s:

```bash
sudo rm -f /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml
sudo rm -f /etc/rancher/k3s/authentication/tsidp.yaml
sudo systemctl restart k3s
sudo systemctl is-active --quiet k3s
sudo k3s kubectl get --raw='/readyz?verbose'
```

This disables OIDC-backed Headlamp access but does not alter the Tailscale API-proxy auth-mode path for `kubectl`. Do not delete the `tsidp` PVC: it stores issuer, signing, registration, and refresh-token state.

## Checklist

- [ ] Tailscale API proxy remains in `mode: "true"`.
- [ ] A dedicated Headlamp client has the exact `/oidc-callback` redirect URI.
- [ ] The Headlamp client secret is stored only in a SealedSecret and the local secret-manager/keyring.
- [ ] k3s accepts the Headlamp client ID as the OIDC audience.
- [ ] `ClusterRoleBinding/tsidp-viewer` remains reconciled.
- [ ] Headlamp forwards the personal token; no ServiceAccount token is used as the user identity.
- [ ] Headlamp user can read permitted resources but cannot read Secrets or write resources.
- [ ] Existing Tailnet-authenticated administrator `kubectl` access still works.

## Related documentation

- [`infrastructure/controllers/tsidp/README.md`](../../infrastructure/controllers/tsidp/README.md)
- [`monitoring/controllers/headlamp/release.yaml`](../../monitoring/controllers/headlamp/release.yaml)
- [Secret Management](../security/secret-management.md)
- [Repository Structure](../standards/repository-structure.md)
