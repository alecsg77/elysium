### Service-link safeguard

The Kubernetes Service is named `tsidp`, which would normally inject a service-link environment variable named `TSIDP_PORT`. The official image uses that same name for an integer listener port, so the HelmRelease sets `podSpec.enableServiceLinks: false`. Keep this setting; otherwise the container exits with an invalid integer `TSIDP_PORT` error before it can join the tailnet.

