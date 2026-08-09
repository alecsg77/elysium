# tsidp OIDC for k3s

This runbook enables personal OIDC authentication to the k3s API through the private `tsidp` issuer, then grants the first human role as read-only Kubernetes access.

The rollout deliberately has two separate enforcement points:

1. Tailscale grants control which Tailnet identities can reach the issuer and API endpoint.
2. k3s authenticates the OIDC token; Kubernetes RBAC authorizes the resulting prefixed identity.

Do not use a shared ServiceAccount token or a static Kubernetes token for a human user. Do not enable Tailscale API-proxy `noauth`, Headlamp OIDC, or an operator role during this first read-only rollout.

## Current prerequisites

Complete these checks before changing the k3s server:

- `HelmRelease/tsidp` is `Ready` and its persistent PVC exists.
- Discovery and JWKS work from a normal, authorized Tailnet device.
- Discovery and JWKS work from the k3s control-plane host.
- The Tailnet policy permits `tag:k8s` to reach `tag:tsidp` on TCP 443.
- An authorized human identity can complete an Authorization Code with PKCE flow and receives `groups: ["viewer"]`.
- An OIDC client is registered for the Kubernetes CLI test. Record its client ID locally; never commit its client secret or a private issuer hostname.
- A current break-glass kubeconfig using the existing administrator credential has been tested from the control-plane host.

k3s `v1.36.3+k3s1` supports the stable `AuthenticationConfiguration` API used below. This deployment does not use the legacy `--oidc-*` flags.

## 1. Record the private values locally

On the k3s control-plane host, set the exact issuer URL and the client ID that will be the token audience for this first Kubernetes test. These values are private infrastructure identifiers; keep them out of Git and shell history where possible.

```bash
read -rp 'OIDC issuer URL: ' IDP_ISSUER
read -rp 'Kubernetes OIDC client ID: ' K8S_OIDC_CLIENT_ID
export IDP_ISSUER K8S_OIDC_CLIENT_ID
```

Verify both discovery and JWKS through the same network path k3s will use:

```bash
curl --fail --silent --show-error \
  "$IDP_ISSUER/.well-known/openid-configuration" \
  | jq '{issuer, jwks_uri, authorization_endpoint, token_endpoint}'

JWKS_URI="$(curl --fail --silent --show-error \
  "$IDP_ISSUER/.well-known/openid-configuration" \
  | jq -r '.jwks_uri')"
curl --fail --silent --show-error "$JWKS_URI" | jq '.keys | length'
```

Expected result: discovery reports the exact issuer entered above, and the JWKS command returns a positive key count.

## 2. Inspect existing k3s API-server configuration

Keep the current administrator session open while making this change. Do not perform the first rollout over the same experimental OIDC credential being enabled.

```bash
sudo systemctl status k3s --no-pager
sudo grep -RIn --include='*.yaml' --include='*.yml' \
  'kube-apiserver-arg\|oidc-\|authentication-config' \
  /etc/rancher/k3s/config.yaml /etc/rancher/k3s/config.yaml.d 2>/dev/null || true
```

If any legacy `--oidc-*` API-server argument is already configured, stop and remove or migrate it as part of this change. Kubernetes does not support mixing the legacy OIDC flags with `--authentication-config`.

Also inspect every k3s drop-in for `kube-apiserver-arg`. k3s list values replace earlier values unless the key ends in `+`; the drop-in created below deliberately uses `kube-apiserver-arg+` so it appends rather than discards existing API-server arguments.

## 3. Create the structured authentication configuration

Create a root-readable configuration file on the control-plane host. The `sub` claim becomes `tsidp:<subject>` and the test token claim `groups: ["viewer"]` becomes the Kubernetes group `tsidp:viewer`.

```bash
sudo install -d -m 0700 /etc/rancher/k3s/authentication

sudo tee /etc/rancher/k3s/authentication/tsidp.yaml >/dev/null <<EOF_CONFIG
apiVersion: apiserver.config.k8s.io/v1
kind: AuthenticationConfiguration
jwt:
  - issuer:
      url: ${IDP_ISSUER}
      audiences:
        - ${K8S_OIDC_CLIENT_ID}
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
sudo sed -n '1,80p' /etc/rancher/k3s/authentication/tsidp.yaml
```

Leave `anonymous` out of this file. k3s starts the API server with anonymous authentication disabled; explicitly configuring `anonymous` in `AuthenticationConfiguration` would conflict with that API-server flag.

The configuration intentionally has no mapping for `email`, `username`, Tailscale tags, or unprefixed groups. `sub` is the stable personal identity for Kubernetes, and `groups` is the only claim used for this first RBAC role.

## 4. Add the k3s API-server argument

Create a dedicated drop-in rather than editing the main k3s configuration file:

```bash
sudo tee /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml >/dev/null <<'EOF_CONFIG'
kube-apiserver-arg+:
  - authentication-config=/etc/rancher/k3s/authentication/tsidp.yaml
EOF_CONFIG

sudo chown root:root /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml
sudo chmod 0600 /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml
sudo cat /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml
```

Do not add `--oidc-issuer-url`, `--oidc-client-id`, `--oidc-username-claim`, or `--oidc-groups-claim`. Those legacy flags must remain absent when `authentication-config` is in use.

## 5. Restart and validate the control plane

This first addition changes the k3s server process arguments and requires a restart. Plan a short API-server interruption and keep the break-glass shell open.

```bash
sudo systemctl restart k3s
sudo systemctl is-active --quiet k3s
sudo journalctl -u k3s -b --no-pager -n 150
sudo k3s kubectl get --raw='/readyz?verbose'
```

Expected result: `k3s` is active and the readiness response ends in `ok`. If the service does not become active, follow [Rollback](#rollback) immediately; do not continue to RBAC or token testing.

## 6. Add the first read-only RBAC binding through GitOps

Use the built-in Kubernetes `view` ClusterRole for the first rollout. It provides namespace-scoped read-only access and deliberately does not grant Secret reads or write access.

Create the following resource as a new Git-managed manifest under `infrastructure/configs/` and add it to that layer's `kustomization.yaml`. Do not use `kubectl apply` for this persistent cluster change.

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

Before committing, render the affected GitOps layer and lint changed YAML. After Flux reconciles, verify with the existing administrator credential:

```bash
kubectl get clusterrolebinding tsidp-viewer -o yaml
kubectl auth can-i get secrets --all-namespaces \
  --as='tsidp:smoke-test' --as-group='tsidp:viewer'
```

The impersonation check must return `no` for Secrets. An administrator must not use it as proof that the OIDC flow works; the next step tests an actual signed ID token.

## 7. Authenticate as the OIDC user and prove RBAC

Use the dedicated Kubernetes CLI OIDC client and an Authorization Code with PKCE flow from a Tailnet-connected workstation. The issued ID token must have:

- `iss` equal to the configured private issuer URL;
- `aud` containing `K8S_OIDC_CLIENT_ID`;
- a non-empty `sub`;
- `groups` containing `viewer`.

For a one-time smoke test, place only the short-lived ID token in a local temporary file with user-only permissions. Do not paste it into a terminal history, chat, Git, a Kubernetes Secret, or a kubeconfig committed to Git.

For the temporary PowerShell tester used to validate the client, add the following immediately after it assigns `$claims = ConvertFrom-JwtPayload $tokens.id_token`. This writes only the short-lived ID token to the current user's temporary directory; delete the file after the smoke test.

```powershell
$tokenPath = Join-Path $env:TEMP 'tsidp-id-token.txt'
[System.IO.File]::WriteAllText(
    $tokenPath,
    $tokens.id_token,
    [System.Text.UTF8Encoding]::new($false)
)
& icacls $tokenPath /inheritance:r /grant:r "${env:USERNAME}:(R)" | Out-Null
Write-Host "Temporary ID token written to $tokenPath" -ForegroundColor Yellow
```

On Windows PowerShell, assuming the local test script has written the token to `$env:TEMP\tsidp-id-token.txt`:

```powershell
$idToken = [System.IO.File]::ReadAllText("$env:TEMP\tsidp-id-token.txt").Trim()

kubectl auth whoami --token $idToken
kubectl auth can-i get pods --all-namespaces --token $idToken
kubectl auth can-i get secrets --all-namespaces --token $idToken

Remove-Item "$env:TEMP\tsidp-id-token.txt" -Force
Remove-Variable idToken
```

Expected results:

- `kubectl auth whoami` reports a username beginning with `tsidp:` and a group `tsidp:viewer` (as well as standard authenticated groups).
- `get pods --all-namespaces` returns `yes`.
- `get secrets --all-namespaces` returns `no`.

A future persistent client configuration should use an OIDC-aware `kubectl` credential plugin that renews tokens interactively. Do not build a long-lived kubeconfig around a copied ID token.

## Rollback

If k3s cannot start, or the API server becomes unhealthy after Step 5, remove only the new OIDC argument and configuration, then restart using the already-tested break-glass session:

```bash
sudo rm -f /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml
sudo rm -f /etc/rancher/k3s/authentication/tsidp.yaml
sudo systemctl restart k3s
sudo systemctl is-active --quiet k3s
sudo k3s kubectl get --raw='/readyz?verbose'
```

If authentication works but authorization is wrong, revert the Git commit that added `ClusterRoleBinding/tsidp-viewer` and reconcile `infra-configs`. Do not remove the `tsidp` PVC during an OIDC or RBAC rollback: it contains issuer and registered-client state.

## Checklist

- [ ] Break-glass administrator access tested before the restart.
- [ ] Private issuer and client ID verified from the control-plane host.
- [ ] No legacy `--oidc-*` arguments coexist with `authentication-config`.
- [ ] k3s is active and `/readyz` is `ok` after the restart.
- [ ] `tsidp:viewer` binding was committed and reconciled through Flux.
- [ ] An actual ID token authenticates as `tsidp:<subject>`.
- [ ] `tsidp:viewer` can read permitted namespace-scoped resources but cannot read Secrets.
- [ ] The temporary ID token was removed from the workstation.

## Related documentation

- [`infrastructure/controllers/tsidp/README.md`](../../infrastructure/controllers/tsidp/README.md)
- [Repository Structure](../standards/repository-structure.md)
- [Secret Management](../security/secret-management.md)
