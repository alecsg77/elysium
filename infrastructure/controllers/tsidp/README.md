# tsidp

`tsidp` is deployed as a single persistent pod in the existing `tailscale` namespace. It uses the official `ghcr.io/tailscale/tsidp` image through the local `charts/onechart` chart because upstream publishes a Docker image but no official Helm chart.

## Required secret

Create `Secret/tsidp-auth` in namespace `tailscale` **before** Flux reconciles `HelmRelease/tsidp`. It must contain exactly one key named `TS_AUTHKEY`, whose value is a narrow, revocable Tailscale auth key or OAuth client secret. When using an OAuth client secret, its client needs the documented **Auth Keys: Write** scope and the pod advertises `tag:tsidp`.

The release does not enable OAuth token exchange (STS). Enable that optional capability only after a concrete workload requires it and its audience/resource restrictions have been reviewed.

Create the encrypted manifest locally; do not commit the plaintext Secret:

```bash
read -rs TS_AUTHKEY
printf '%s' "$TS_AUTHKEY" \
  | kubectl create secret generic tsidp-auth \
      --namespace tailscale \
      --from-file=TS_AUTHKEY=/dev/stdin \
      --dry-run=client --output yaml \
  | kubeseal --cert etc/certs/pub-sealed-secrets.pem --format yaml \
  > infrastructure/controllers/tsidp/tsidp-auth-sealed-secret.yaml
unset TS_AUTHKEY
```

Add the resulting encrypted file to `kustomization.yaml` locally, verify its diff has no plaintext, then commit it in the same change that enables the release. The auth key must be tag-scoped, revocable, and not be the Tailscale Operator credential.

## Persistent state

The release creates the `tsidp-tsidp-data` PVC. It stores both tsnet and OIDC server state, including registered clients and refresh-token state. Do not delete this PVC during a HelmRelease rollback or upgrade. Back it up and test restoration before upgrading `tsidp`.

See [`docs/runbooks/tsidp-sso.md`](../../../docs/runbooks/tsidp-sso.md) for the required Tailscale policy, k3s configuration, test sequence, and recovery process.
