# Grafana MCP Server

## Overview

Grafana MCP (Model Context Protocol) Server enables AI assistants and automation tools to interact with Grafana programmatically through the standardized MCP protocol. This deployment provides access to:

- **Dashboards**: Query, create, and update Grafana dashboards
- **Data Sources**: Query metrics from Prometheus, Loki, and Tempo
- **Alerting**: Manage alert rules and notification channels
- **Annotations**: Create and query annotations
- **Users & Teams**: Manage Grafana users and teams

## Architecture

- **Namespace**: `monitoring`
- **Chart**: `grafana-mcp` (official Grafana Helm chart)
- **Image**: `docker.io/mcp/grafana` (official Docker image)
- **Dependencies**: `kube-prometheus-stack` (Grafana deployment)
- **Access**: Private via Tailscale ingress at `https://grafana-mcp.${ts_net}`
- **Port**: 8000 (SSE transport by default)

## Prerequisites

### 1. Create Grafana Service Account

The service account role determines the available permissions:

- **Editor role**: Full read/write access (recommended for development and working scenarios)
- **Viewer role**: Read-only access (recommended for troubleshooting scenarios)

**Steps**:
1. Open Grafana UI at `https://grafana.${ts_net}`
2. Navigate to: **Administration** → **Service Accounts**
3. Click **Add service account**
4. Configure:
   - **Display name**: `grafana-mcp-server` (or `grafana-mcp-readonly` for read-only)
   - **Role**: `Editor` or `Viewer` (based on use case)
5. Click **Create**
6. Click **Add service account token**
7. Copy the generated token (it won't be shown again)

### 2. Create Sealed Secret

Replace `<your-token-from-grafana>` with the token from step 1:

```bash
kubectl create secret generic grafana-mcp-credentials \
  --namespace=monitoring \
  --from-literal=GRAFANA_URL='http://kube-prometheus-stack-grafana.monitoring.svc.cluster.local:80' \
  --from-literal=GRAFANA_SERVICE_ACCOUNT_TOKEN='<your-token-from-grafana>' \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > monitoring/controllers/grafana-mcp/grafana-mcp-credentials-sealed-secret.yaml
```

### 3. Commit and Deploy

```bash
# Commit the sealed secret
git add monitoring/controllers/grafana-mcp/
git commit -m "chore(monitoring): add grafana-mcp sealed secret"
git push

# Flux will automatically deploy within 1-5 minutes
```

## Configuration Reference

### Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `GRAFANA_URL` | Sealed Secret | Internal Grafana service URL |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | Sealed Secret | Service account token for authentication |

### Endpoints

| Endpoint | URL | Description |
|----------|-----|-------------|
| **SSE Endpoint** | `https://grafana-mcp.${ts_net}` | Server-Sent Events stream (default transport) |
| **Internal Service** | `grafana-mcp.monitoring.svc.cluster.local:8000` | Cluster-internal access |

### Resources

| Resource | Request | Limit |
|----------|---------|-------|
| **CPU** | 100m | 500m |
| **Memory** | 256Mi | 512Mi |

### Grafana Service Account Permissions

**Editor Role** (Full Access):
- `datasources:*` - Read and query data sources
- `dashboards:*` - Read, create, and update dashboards
- `folders:*` - Read folders
- `teams:*` - Read teams
- `global.users:*` - Read users
- `alert.rules:read` - Read alert rules
- `alert.notifications:read` - Read notifications
- `annotations:*` - Read and write annotations

**Viewer Role** (Read-Only Access):
- `datasources:read` - Read and query data sources
- `dashboards:read` - Read dashboards
- `folders:read` - Read folders
- `teams:read` - Read teams
- `global.users:read` - Read users
- `alert.rules:read` - Read alert rules
- `alert.notifications:read` - Read notifications
- `annotations:read` - Read annotations

## MCP Client Configuration

This section covers 4 different usage scenarios for connecting to the Grafana MCP server.

### Scenario 1: DevContainer in Cluster (Coder)

**Use Case**: Working inside a devcontainer deployed in the cluster using Coder DevContainer Template.

**Access Method**: Direct cluster service access (internal DNS)

**Permissions**: Full read/write (Editor role)

**Configuration** (`.mcp-config.json` or IDE settings):
```json
{
  "mcpServers": {
    "grafana": {
      "url": "http://grafana-mcp.monitoring.svc.cluster.local:8000",
      "transport": "sse"
    }
  }
}
```

**Notes**:
- Uses internal Kubernetes DNS
- No Tailscale required (already inside cluster network)
- Direct service-to-service communication
- Low latency

### Scenario 2: DevContainer via Codespaces + Tailscale

**Use Case**: Working inside a devcontainer using GitHub Codespaces with Tailscale connection to cluster network.

**Access Method**: Tailscale ingress (private network overlay)

**Permissions**: Full read/write (Editor role)

**Configuration** (`.mcp-config.json` or IDE settings):
```json
{
  "mcpServers": {
    "grafana": {
      "url": "https://grafana-mcp.${ts_net}",
      "transport": "sse"
    }
  }
}
```

**Prerequisites**:
- Tailscale installed and authenticated in Codespaces
- Connected to the cluster's Tailscale network
- Access to `*.${ts_net}` domain

**Notes**:
- Secure access over Tailscale mesh network
- HTTPS with automatic TLS via Tailscale
- Can access from anywhere with Tailscale

### Scenario 3: Local DevContainer on PC (VSCode)

**Use Case**: Working inside a devcontainer on your own PC using VSCode devcontainer capabilities, connected to Tailscale network.

**Access Method**: Tailscale ingress (private network overlay)

**Permissions**: Full read/write (Editor role)

**Configuration** (`.mcp-config.json` or IDE settings):
```json
{
  "mcpServers": {
    "grafana": {
      "url": "https://grafana-mcp.${ts_net}",
      "transport": "sse"
    }
  }
}
```

**Prerequisites**:
- Tailscale installed on local PC
- Connected to the cluster's Tailscale network
- Docker Desktop or equivalent container runtime

**Notes**:
- Same configuration as Scenario 2
- Works from local development environment
- Requires local Tailscale client

### Scenario 4: GitHub Copilot Agent (ARC)

**Use Case**: Troubleshooting with GitHub Copilot coding agent running inside the cluster using Actions Runner Controller (ARC).

**Access Method**: Direct cluster service access (internal DNS)

**Permissions**: Read-only (Viewer role recommended for safety)

**Configuration** (GitHub Repository MCP Settings):

Navigate to repository settings → Copilot → MCP Servers and configure:

```json
{
  "mcpServers": {
    "grafana": {
      "url": "http://grafana-mcp.monitoring.svc.cluster.local:8000",
      "transport": "sse"
    }
  }
}
```

**Recommended Setup for Read-Only Access**:

1. Create a separate service account with **Viewer** role:
   ```bash
   # In Grafana UI: Create service account "grafana-mcp-readonly" with Viewer role
   ```

2. Create a read-only sealed secret (optional, for dedicated read-only deployment):
   ```bash
   kubectl create secret generic grafana-mcp-readonly-credentials \
     --namespace=monitoring \
     --from-literal=GRAFANA_URL='http://kube-prometheus-stack-grafana.monitoring.svc.cluster.local:80' \
     --from-literal=GRAFANA_SERVICE_ACCOUNT_TOKEN='<readonly-token>' \
     --dry-run=client -o yaml | \
     kubeseal --cert etc/certs/pub-sealed-secrets.pem \
     --format=yaml > monitoring/controllers/grafana-mcp/grafana-mcp-readonly-credentials-sealed-secret.yaml
   ```

**Notes**:
- Viewer role limits agent to read-only operations
- Prevents accidental modifications during troubleshooting
- Same internal DNS access as Scenario 1
- GitHub Copilot agent runs in `arc-runners` namespace
- Automatic service discovery via Kubernetes DNS

## Usage Examples

### Query Prometheus Metrics

```json
{
  "method": "tools/call",
  "params": {
    "name": "prometheus_query",
    "arguments": {
      "query": "up{job='kubernetes-nodes'}",
      "datasource": "Prometheus"
    }
  }
}
```

### Query Loki Logs

```json
{
  "method": "tools/call",
  "params": {
    "name": "loki_query",
    "arguments": {
      "query": "{namespace=\"monitoring\"}",
      "datasource": "Loki"
    }
  }
}
```

### Create Dashboard (Editor role only)

```json
{
  "method": "tools/call",
  "params": {
    "name": "create_dashboard",
    "arguments": {
      "title": "My Custom Dashboard",
      "folder": "General",
      "panels": [...]
    }
  }
}
```

### Read Dashboard (Any role)

```json
{
  "method": "tools/call",
  "params": {
    "name": "get_dashboard",
    "arguments": {
      "uid": "dashboard-uid"
    }
  }
}
```

## Validation Steps

### 1. Check HelmRelease Status

```bash
kubectl get hr -n monitoring grafana-mcp
```

Expected output:
```
NAME          AGE   READY   STATUS
grafana-mcp   2m    True    Release reconciliation succeeded
```

### 2. Verify Pod is Running

```bash
kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana-mcp
```

Expected output:
```
NAME                           READY   STATUS    RESTARTS   AGE
grafana-mcp-<hash>-<hash>      1/1     Running   0          2m
```

### 3. Test SSE Endpoint (from Tailscale network)

```bash
curl -N https://grafana-mcp.${ts_net}
```

Expected: SSE event stream (connection stays open)

### 4. Test from Inside Cluster

```bash
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl -N http://grafana-mcp.monitoring.svc.cluster.local:8000
```

Expected: SSE event stream

### 5. Check Logs

```bash
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana-mcp --tail=100
```

Look for:
- Successful connection to Grafana
- No authentication errors
- SSE server listening on port 8000

### 6. Verify Grafana Connectivity

```bash
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana-mcp | grep -i grafana
```

Expected: Log lines showing successful Grafana API calls

## Maintenance

### Token Rotation

Rotate the service account token periodically (quarterly recommended):

1. Generate new token in Grafana UI (Service Accounts → grafana-mcp-server → Tokens)
2. Create new sealed secret with updated token
3. Apply the updated sealed secret
4. Restart the pod: `kubectl rollout restart deployment -n monitoring grafana-mcp`

### View Logs

```bash
# Real-time logs
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana-mcp -f

# Last 100 lines
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana-mcp --tail=100

# Logs from previous container (if crashed)
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana-mcp --previous
```

### Update Configuration

To update environment variables:

1. Edit `monitoring/controllers/grafana-mcp/grafana-mcp-credentials-sealed-secret.yaml`
2. Regenerate sealed secret with new values
3. Commit and push
4. Flux will reconcile within 1 hour (or force: `flux reconcile hr grafana-mcp -n monitoring`)

## Troubleshooting

### Pod Not Starting

**Symptom**: Pod in `CrashLoopBackOff` or `Error` state

**Common Causes**:
1. **Missing/invalid token**: Check sealed secret decrypted correctly
   ```bash
   kubectl get secret grafana-mcp-credentials -n monitoring -o yaml
   ```
2. **Grafana not ready**: Check kube-prometheus-stack status
   ```bash
   kubectl get hr -n monitoring kube-prometheus-stack
   ```

**Resolution**:
- View logs: `kubectl logs -n monitoring -l app.kubernetes.io/name=grafana-mcp`
- Check events: `kubectl get events -n monitoring --sort-by='.lastTimestamp'`

### Authentication Errors

**Symptom**: Logs show `401 Unauthorized` or `403 Forbidden`

**Causes**:
1. Invalid service account token
2. Insufficient permissions on service account
3. Grafana service account disabled

**Resolution**:
1. Verify token in Grafana UI (Service Accounts)
2. Ensure service account has appropriate role (Editor or Viewer)
3. Regenerate token and update sealed secret

### Connection Timeout

**Symptom**: Cannot reach Grafana from MCP server

**Causes**:
1. Incorrect `GRAFANA_URL` in sealed secret
2. Network policy blocking traffic
3. Grafana service not ready

**Resolution**:
1. Test connectivity from pod:
   ```bash
   kubectl exec -it -n monitoring <grafana-mcp-pod> -- sh
   # Inside pod:
   curl http://kube-prometheus-stack-grafana.monitoring.svc.cluster.local:80/api/health
   ```
2. Check Grafana service exists:
   ```bash
   kubectl get svc -n monitoring kube-prometheus-stack-grafana
   ```

### Ingress Not Working

**Symptom**: Cannot access `https://grafana-mcp.${ts_net}`

**Causes**:
1. Tailscale operator not ready
2. DNS not propagated
3. Ingress misconfigured

**Resolution**:
1. Check ingress status:
   ```bash
   kubectl get ingress -n monitoring grafana-mcp
   ```
2. Verify Tailscale operator:
   ```bash
   kubectl get pods -n tailscale
   ```
3. Check Tailscale DNS:
   ```bash
   tailscale status
   ```

### MCP Client Connection Issues

**Symptom**: MCP client cannot connect to server

**Troubleshooting by Scenario**:

**Scenario 1 & 4 (In-Cluster)**:
```bash
# Verify service is accessible
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl -v http://grafana-mcp.monitoring.svc.cluster.local:8000
```

**Scenario 2 & 3 (Tailscale)**:
```bash
# Verify Tailscale connection
tailscale status

# Test endpoint
curl -v https://grafana-mcp.${ts_net}
```

## References

- [Grafana MCP GitHub Repository](https://github.com/grafana/mcp-grafana)
- [Grafana MCP Docker Image](https://hub.docker.com/r/mcp/grafana)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Grafana Service Accounts Documentation](https://grafana.com/docs/grafana/latest/administration/service-accounts/)
- [Grafana Helm Charts](https://github.com/grafana/helm-charts)
- [Flux HelmRelease Documentation](https://fluxcd.io/docs/components/helm/helmreleases/)

## Related Components

- **kube-prometheus-stack**: Provides Grafana instance
- **Tailscale Operator**: Provides private network access
- **Sealed Secrets**: Encrypts sensitive credentials
- **Flux**: GitOps continuous delivery
- **Actions Runner Controller (ARC)**: GitHub Actions self-hosted runners for Copilot agent

## Security Considerations

- Service account token stored encrypted with Sealed Secrets
- Pod runs as non-root user (default from Helm chart)
- All capabilities dropped from container (default from Helm chart)
- Access restricted to Tailscale network for external access
- Internal cluster access for in-cluster workloads
- Token rotation recommended quarterly
- Use Viewer role for read-only scenarios (troubleshooting)
- Use Editor role for full read/write access (development)
- Audit logs available in Grafana for API access tracking
