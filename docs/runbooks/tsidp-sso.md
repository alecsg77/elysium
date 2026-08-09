# Configure k3s OIDC with tsidp

This runbook configures k3s to accept the personal OIDC tokens already issued by the private `tsidp` deployment and configures a Windows `kubelogin` client to renew them interactively.

There is no intermediate application or manual token-copy workflow in this design:

```text
kubectl -> kubelogin -> tsidp authorization-code flow -> ID token -> k3s -> Kubernetes RBAC
```

Tailscale grants control which human identities can reach `tsidp` and the Kubernetes API endpoint. k3s validates the signed OIDC token. Kubernetes RBAC authorizes the prefixed user and group from that token.

This first role is read-only. Do not use a shared ServiceAccount token or a static Kubernetes token for human access. Do not enable Tailscale API-proxy `noauth`, Headlamp OIDC, or an operator role in this change.

## Prerequisites

Before editing the k3s control-plane host, confirm all of the following:

- `HelmRelease/tsidp` is `Ready` and its persistent PVC exists.
- Discovery and JWKS work from the k3s control-plane host.
- Tailnet policy permits `tag:k8s` to reach `tag:tsidp` on TCP 443.
- Your Tailnet identity receives `groups: ["viewer"]` from `tsidp`.
- You have one registered OIDC client for `kubelogin` with the exact redirect URI `http://127.0.0.1:8765/callback`.
- Its client ID is available locally. Its client secret is available only on the workstation where `kubelogin` will run.
- A break-glass administrator kubeconfig has been tested from the control-plane host and remains open during the restart.

Use the existing client only if its secret has been rotated after the earlier temporary test. Otherwise, rotate that secret in `tsidp` first. The client is now the direct personal `kubelogin` client; it is not an intermediate application.

k3s `v1.36.3+k3s1` supports the stable `AuthenticationConfiguration` API used below. Do not combine it with legacy `--oidc-*` flags.

## 1. Configure the k3s API server

### 1.1 Record the issuer and audience locally

On the k3s control-plane host, enter the exact issuer URL and the client ID of the direct `kubelogin` client. These are private infrastructure values: do not commit them to Git.

```bash
read -rp 'OIDC issuer URL: ' IDP_ISSUER
read -rp 'kubelogin client ID: ' K8S_OIDC_CLIENT_ID
export IDP_ISSUER K8S_OIDC_CLIENT_ID
```

Verify discovery and JWKS over the exact path k3s will use:

```bash
curl --fail --silent --show-error \
  "$IDP_ISSUER/.well-known/openid-configuration" \
  | jq '{issuer, jwks_uri}'

JWKS_URI="$(curl --fail --silent --show-error \
  "$IDP_ISSUER/.well-known/openid-configuration" \
  | jq -r '.jwks_uri')"
curl --fail --silent --show-error "$JWKS_URI" | jq '.keys | length'
```

The returned `issuer` must exactly equal `IDP_ISSUER`, and the JWKS key count must be greater than zero.

### 1.2 Check for incompatible legacy OIDC flags

Keep the break-glass administrator session open. Inspect the current k3s configuration before adding anything:

```bash
sudo grep -RIn --include='*.yaml' --include='*.yml' \
  'kube-apiserver-arg\|oidc-\|authentication-config' \
  /etc/rancher/k3s/config.yaml /etc/rancher/k3s/config.yaml.d 2>/dev/null || true
```

If any `oidc-*` API-server argument exists, remove or migrate it before continuing. Kubernetes exits on startup when `--authentication-config` is combined with `--oidc-*` flags.

### 1.3 Create the authentication configuration

This maps token `sub` to `tsidp:<subject>` and token `groups: ["viewer"]` to Kubernetes group `tsidp:viewer`.

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

Leave `anonymous` out of this file. k3s starts the API server with anonymous authentication disabled, and configuring `anonymous` in this file would conflict with the existing API-server flag.

### 1.4 Load the authentication configuration

Create a dedicated k3s drop-in. `kube-apiserver-arg+` appends this argument without replacing any existing API-server arguments.

```bash
sudo tee /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml >/dev/null <<'EOF_CONFIG'
kube-apiserver-arg+:
  - authentication-config=/etc/rancher/k3s/authentication/tsidp.yaml
EOF_CONFIG

sudo chown root:root /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml
sudo chmod 0600 /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml
sudo cat /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml
```

### 1.5 Restart and validate k3s

This causes a short API-server interruption. Keep the break-glass shell open until all checks pass.

```bash
sudo systemctl restart k3s
sudo systemctl is-active --quiet k3s
sudo journalctl -u k3s -b --no-pager -n 150
sudo k3s kubectl get --raw='/readyz?verbose'
```

The service must be active and `/readyz` must end in `ok`. If not, go directly to [Rollback](#rollback); do not proceed to RBAC or client configuration.

## 2. Bind the `viewer` claim through GitOps

The token is now acceptable to k3s, but it has no Kubernetes permissions until RBAC is reconciled. Add this one resource under `infrastructure/configs/` and add it to `infrastructure/configs/kustomization.yaml`:

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

The built-in `view` ClusterRole provides namespace-scoped read-only access and deliberately excludes Secret reads and writes. Commit the manifest, let Flux reconcile `infra-configs`, then verify with the break-glass credential:

```bash
kubectl get clusterrolebinding tsidp-viewer -o yaml
kubectl auth can-i get pods --all-namespaces \
  --as='tsidp:smoke-test' --as-group='tsidp:viewer'
kubectl auth can-i get secrets --all-namespaces \
  --as='tsidp:smoke-test' --as-group='tsidp:viewer'
```

Expected results are `yes` for Pod reads and `no` for Secret reads.

## 3. Configure kubelogin on Windows

Perform this on the Windows workstation already connected to the Tailnet. This configuration uses the registered `kubelogin` client directly and opens the normal browser login when tokens need renewal.

### 3.1 Install kubelogin

In PowerShell:

```powershell
winget install --id int128.kubelogin --exact
kubectl oidc-login --help
```

If `winget` reports that the package is already installed, keep the installed version only if `kubectl oidc-login --help` succeeds. `kubelogin` is used as a `kubectl` exec credential plugin; no permanent ID token is stored in the kubeconfig.

### 3.2 Create a separate personal kubeconfig

Do not overwrite or share the administrator kubeconfig. This starts with a local copy so the existing cluster endpoint and certificate authority remain intact.

```powershell
$SourceKubeconfig = "$HOME\.kube\config"       # change if your working kubeconfig is elsewhere
$OidcKubeconfig = "$HOME\.kube\kyrion-tsidp.yaml"

Copy-Item -LiteralPath $SourceKubeconfig -Destination $OidcKubeconfig -Force
$env:KUBECONFIG = $OidcKubeconfig

$ClusterName = kubectl config view --minify -o jsonpath='{.clusters[0].name}'
if ([string]::IsNullOrWhiteSpace($ClusterName)) {
    throw 'No current cluster was found in the copied kubeconfig.'
}
```

Restrict the local file to your Windows account. The registered OIDC client secret is stored in the exec configuration, so this kubeconfig must remain private and must never be committed, emailed, or shared.

```powershell
icacls $OidcKubeconfig /inheritance:r /grant:r "${env:USERNAME}:(R,W)" | Out-Null
```

### 3.3 Add the direct OIDC exec credential

Enter the private issuer, client ID, and the rotated client secret. The secret is requested interactively and is not put into PowerShell history.

```powershell
$Issuer = Read-Host 'OIDC issuer URL'
$ClientId = Read-Host 'kubelogin client ID'
$SecureClientSecret = Read-Host 'kubelogin client secret' -AsSecureString
$SecretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureClientSecret)

try {
    $ClientSecret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($SecretPointer)

    kubectl config set-credentials tsidp `
      --exec-command=kubectl `
      --exec-api-version=client.authentication.k8s.io/v1 `
      --exec-interactive-mode=Never `
      --exec-arg=oidc-login `
      --exec-arg=--grant-type=authcode `
      --exec-arg=get-token `
      --exec-arg="--oidc-issuer-url=$Issuer" `
      --exec-arg="--oidc-client-id=$ClientId" `
      --exec-arg="--oidc-client-secret=$ClientSecret" `
      --exec-arg=--listen-address=127.0.0.1:8765 `
      --exec-arg=--oidc-redirect-url=http://127.0.0.1:8765/callback `
      --exec-arg=--token-cache-storage=keyring
}
finally {
    if ($SecretPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($SecretPointer)
    }
    Remove-Variable ClientSecret -ErrorAction SilentlyContinue
}

kubectl config set-context tsidp --cluster=$ClusterName --user=tsidp
```

The redirect URL must exactly match the URI registered in `tsidp`: `http://127.0.0.1:8765/callback`. `--token-cache-storage=keyring` stores refresh-token state in the Windows keyring instead of a filesystem cache.

### 3.4 Login and verify effective access

The first command opens the browser and performs the authorization-code flow. Subsequent commands reuse or refresh the cached session as needed.

```powershell
kubectl --context tsidp auth whoami
kubectl --context tsidp auth can-i get pods --all-namespaces
kubectl --context tsidp auth can-i get secrets --all-namespaces
kubectl --context tsidp get pods --all-namespaces
```

Expected results:

- `auth whoami` shows a username beginning with `tsidp:` and group `tsidp:viewer`.
- Pod reads are allowed.
- Secret reads are denied.

Use the personal kubeconfig explicitly, or make the context current only after the checks succeed:

```powershell
$env:KUBECONFIG = "$HOME\.kube\kyrion-tsidp.yaml"
kubectl config use-context tsidp
```

## Troubleshooting

| Symptom | Likely cause and action |
| --- | --- |
| k3s fails to start after restart | A legacy `--oidc-*` flag remains, the YAML is invalid, or k3s cannot reach issuer discovery/JWKS. Follow [Rollback](#rollback), inspect `journalctl -u k3s -b`, then correct the first error. |
| `kubectl` returns `401 Unauthorized` | Check the issuer URL is exact, the token `aud` is the same client ID configured in `tsidp.yaml`, and the control plane can still retrieve JWKS. |
| `kubectl auth whoami` works but reads are forbidden | OIDC works; Flux has not yet reconciled `ClusterRoleBinding/tsidp-viewer`, or the Tailnet policy did not emit `groups: ["viewer"]` for this user. |
| Browser login does not return to kubelogin | The registered redirect URI must exactly be `http://127.0.0.1:8765/callback`; also ensure no other local process uses port 8765. |
| `kubectl oidc-login` is unknown | Reinstall `int128.kubelogin`, close and reopen PowerShell so PATH refreshes, then rerun `kubectl oidc-login --help`. |

## Rollback

If the k3s API server does not become healthy after Step 1, remove only the OIDC files and restart through the still-open break-glass session:

```bash
sudo rm -f /etc/rancher/k3s/config.yaml.d/90-tsidp-auth.yaml
sudo rm -f /etc/rancher/k3s/authentication/tsidp.yaml
sudo systemctl restart k3s
sudo systemctl is-active --quiet k3s
sudo k3s kubectl get --raw='/readyz?verbose'
```

If OIDC works but read-only authorization is wrong, revert the Git commit that added `ClusterRoleBinding/tsidp-viewer` and reconcile `infra-configs`. Do not delete the `tsidp` PVC during either rollback: it contains issuer, signing, registration, and refresh-token state.

## Checklist

- [ ] Break-glass administrator access was tested before restarting k3s.
- [ ] The control-plane host resolves discovery and JWKS from `tsidp`.
- [ ] No legacy `--oidc-*` flag coexists with `authentication-config`.
- [ ] k3s is active and `/readyz` is `ok` after restart.
- [ ] `tsidp:viewer` was committed and reconciled via Flux.
- [ ] `kubectl --context tsidp auth whoami` shows the prefixed OIDC identity.
- [ ] Pod reads work and Secret reads are denied.
- [ ] The OIDC kubeconfig and client secret remain local and are not shared.

## Related documentation

- [`infrastructure/controllers/tsidp/README.md`](../../infrastructure/controllers/tsidp/README.md)
- [Repository Structure](../standards/repository-structure.md)
- [Secret Management](../security/secret-management.md)
