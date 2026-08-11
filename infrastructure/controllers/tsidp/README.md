# tsidp

`tsidp` is deployed as a single persistent pod in the existing `tailscale` namespace. It uses the official `ghcr.io/tailscale/tsidp` image through the local `charts/onechart` chart because upstream publishes a Docker image but no official Helm chart.

## Service-link environment collision

The `tsidp` Service would otherwise inject `TSIDP_PORT=tcp://...:443` into the pod through Kubernetes Service links. `tsidp` interprets `TSIDP_PORT` as its integer listener-port setting and exits when it receives that URL. Keep `podSpec.enableServiceLinks: false` in the HelmRelease to prevent this collision.

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

## Service-link environment collision

The HelmRelease sets `podSpec.enableServiceLinks: false`. Kubernetes otherwise injects a `TSIDP_PORT=tcp://<service-ip>:443` environment variable for the Service named `tsidp`; the official image interprets `TSIDP_PORT` as an integer listener-port setting and exits. Do not re-enable Service links unless the Service is renamed and the resulting environment-variable collision is tested.

## Health checks

`tsidp` serves HTTPS through its tsnet interface, not the Pod network interface. A Kubernetes TCP probe to the Pod IP on port 443 therefore fails even while the tsnet auth loop is running. The HelmRelease intentionally has no Kubernetes readiness or liveness probe; use the tailnet issuer discovery endpoint and Flux/Pod status as the operational health checks.

## Persistent state

The release creates the `tsidp-tsidp-data` PVC, mounted at `TS_STATE_DIR=/data`. It stores both tsnet and OIDC server state, including issuer signing material, registered clients, and refresh-token state.

The HelmRelease explicitly uses Flux's `RetryOnFailure` strategy for installs and upgrades. This retries a failed action in place rather than uninstalling a failed install or rolling back a failed upgrade, so normal pod restarts, image/chart updates, and transient reconciliation failures retain the claim and its contents. Do not delete this PVC during recovery, rollback, or upgrade.

A deliberate GitOps uninstallation removes the Helm-managed PVC and therefore its state. Back up and test restoration before upgrading `tsidp`; only delete the claim as part of an intentional full uninstall or a documented disaster-recovery procedure.

See [`docs/runbooks/tsidp-sso.md`](../../../docs/runbooks/tsidp-sso.md) for the required Tailscale policy, k3s configuration, test sequence, and recovery process.
