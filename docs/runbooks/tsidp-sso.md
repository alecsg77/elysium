### Service-link safeguard

The Kubernetes Service is named `tsidp`, which would normally inject a service-link environment variable named `TSIDP_PORT`. The official image uses that same name for an integer listener port, so the HelmRelease sets `podSpec.enableServiceLinks: false`. Keep this setting; otherwise the container exits with an invalid integer `TSIDP_PORT` error before it can join the tailnet.

### Kubernetes probe limitation

`tsidp` serves HTTPS through tsnet rather than the Pod network interface. Do not configure a Kubernetes TCP or HTTP probe against the Pod IP on port 443: it returns connection refused even when the tsnet authentication loop is healthy. The HelmRelease intentionally omits these probes; validate the issuer discovery endpoint from a Tailnet client and from the k3s control-plane host instead.

