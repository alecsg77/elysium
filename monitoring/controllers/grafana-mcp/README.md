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
- **Chart**: `onechart` (generic Helm chart for containerized applications)
- **Dependencies**: `kube-prometheus-stack` (Grafana deployment)
- **Transport**: SSE (Server-Sent Events) for web client compatibility
- **Access**: Private via Tailscale ingress at `https://grafana-mcp.${ts_net}`

## Prerequisites

### 1. Create Grafana Service Account

1. Open Grafana UI at `https://grafana.${ts_net}`
2. Navigate to: **Administration** → **Service Accounts**
3. Click **Add service account**
4. Configure:
   - **Display name**: `grafana-mcp-server`
   - **Role**: `Editor` (provides read/write access to dashboards and data sources)
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

### 3. Container Image Availability

**Important**: As of the initial implementation, the Grafana MCP project does not publish official container images to a public registry. You have two options:

#### Option A: Build Custom Image

```bash
# Clone the repository
git clone https://github.com/grafana/mcp-grafana.git
cd mcp-grafana

# Build the Docker image
docker build -t <your-registry>/grafana-mcp:latest .

# Push to your registry
docker push <your-registry>/grafana-mcp:latest

# Update the image reference in release.yaml
# image:
#   repository: <your-registry>/grafana-mcp
#   tag: latest
```

#### Option B: Wait for Official Image

Monitor the [Grafana MCP GitHub repository](https://github.com/grafana/mcp-grafana) for official image releases. Once available, update the image reference in `release.yaml`.

### 4. Commit and Deploy

```bash
# Commit the sealed secret
git add monitoring/controllers/grafana-mcp/
git commit -m "feat(monitoring): deploy grafana-mcp server"
git push

# Flux will automatically deploy within 1-5 minutes
```

## Configuration Reference

### Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `GRAFANA_URL` | Sealed Secret | Internal Grafana service URL |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | Sealed Secret | Service account token for authentication |
| `TRANSPORT` | ConfigMap | Transport mode (`sse` for Server-Sent Events) |
| `DEBUG` | ConfigMap | Enable debug logging (`true`/`false`) |

### Endpoints

| Endpoint | URL | Description |
|----------|-----|-------------|
| **Health Check** | `https://grafana-mcp.${ts_net}/healthz` | Health status endpoint |
| **SSE Endpoint** | `https://grafana-mcp.${ts_net}/sse` | Server-Sent Events stream |
| **Internal Service** | `grafana-mcp.monitoring.svc.cluster.local:8000` | Cluster-internal access |

### Resources

| Resource | Request | Limit |
|----------|---------|-------|
| **CPU** | 100m | 500m |
| **Memory** | 256Mi | 512Mi |

### Grafana Service Account Permissions

The service account requires the following RBAC scopes for full functionality:

- `datasources:*` - Read and query data sources
- `dashboards:*` - Read, create, and update dashboards
- `folders:*` - Read folders
- `teams:*` - Read teams
- `global.users:*` - Read users
- `alert.rules:read` - Read alert rules
- `alert.notifications:read` - Read notifications
- `annotations:*` - Read and write annotations

**Recommended**: Assign the **Editor** role for broad access.

## Usage Examples

### MCP Client Configuration

Configure your MCP client to connect to Grafana MCP:

```json
{
  "mcpServers": {
    "grafana": {
      "url": "https://grafana-mcp.${ts_net}/sse",
      "transport": "sse"
    }
  }
}
```

### Query Prometheus Metrics

Example MCP request to query Prometheus:

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

### Create Dashboard

Example MCP request to create a dashboard:

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

### 3. Test Health Endpoint

```bash
curl https://grafana-mcp.${ts_net}/healthz
```

Expected output:
```json
{"status": "ok"}
```

### 4. Check Logs

```bash
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana-mcp --tail=100
```

Look for:
- Successful connection to Grafana
- No authentication errors
- SSE server listening on port 8000

### 5. Verify Grafana Connectivity

```bash
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana-mcp | grep -i grafana
```

Expected: Log lines showing successful Grafana API calls

### 6. Test MCP SSE Endpoint

```bash
curl -N https://grafana-mcp.${ts_net}/sse
```

Expected: SSE event stream (connection stays open)

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

1. Edit `monitoring/controllers/grafana-mcp/release.yaml`
2. Modify the `vars` section
3. Commit and push
4. Flux will reconcile within 1 hour (or force: `flux reconcile hr grafana-mcp -n monitoring`)

### Scale Replicas

The MCP server is designed to run as a single instance. To change:

1. Edit `release.yaml` → `values.replicas`
2. Commit and push
3. Flux will reconcile automatically

## Troubleshooting

### Pod Not Starting

**Symptom**: Pod in `CrashLoopBackOff` or `Error` state

**Common Causes**:
1. **Missing/invalid token**: Check sealed secret decrypted correctly
   ```bash
   kubectl get secret grafana-mcp-credentials -n monitoring -o yaml
   ```
2. **Image not available**: Build and push custom image (see Prerequisites)
3. **Grafana not ready**: Check kube-prometheus-stack status
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
2. Ensure service account has **Editor** role
3. Regenerate token and update sealed secret

### Health Check Failing

**Symptom**: Readiness/liveness probes failing

**Causes**:
1. Server not listening on expected port
2. Health endpoint path incorrect
3. Server startup timeout

**Resolution**:
1. Check container logs for startup errors
2. Verify `containerPort` matches server configuration
3. Increase `initialDelaySeconds` in probes

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

## References

- [Grafana MCP GitHub Repository](https://github.com/grafana/mcp-grafana)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Grafana Service Accounts Documentation](https://grafana.com/docs/grafana/latest/administration/service-accounts/)
- [OneChart Documentation](https://github.com/gimlet-io/onechart)
- [Flux HelmRelease Documentation](https://fluxcd.io/docs/components/helm/helmreleases/)

## Related Components

- **kube-prometheus-stack**: Provides Grafana instance
- **Tailscale Operator**: Provides private network access
- **Sealed Secrets**: Encrypts sensitive credentials
- **Flux**: GitOps continuous delivery

## Security Considerations

- Service account token stored encrypted with Sealed Secrets
- Pod runs as non-root user (UID 65534)
- All capabilities dropped from container
- Access restricted to Tailscale network only
- Token rotation recommended quarterly
- Audit logs available in Grafana for API access tracking
