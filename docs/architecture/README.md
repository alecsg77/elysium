# Architecture

Overview of cluster topology, networking, storage, and security boundaries.

- Flux CD components and dependency chain
- Network: Traefik, Tailscale, Ingress patterns
- Storage: Local + rclone CSI, PVC management
- Observability: Prometheus, Grafana, Loki, Tempo, Elasticsearch

See repository manifests under:
- clusters/kyrion/
- infrastructure/controllers/
- infrastructure/configs/
