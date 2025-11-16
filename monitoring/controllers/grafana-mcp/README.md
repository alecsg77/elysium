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
- **Image**: `docker.io/grafana/mcp-grafana` (official Docker image)
- **Dependencies**: `kube-prometheus-stack` (Grafana deployment)
- **Access**: Private via Tailscale ingress at `https://grafana-mcp.${ts_net}` or internal cluster DNS
- **Port**: 8000 (SSE transport by default)

## Prerequisites

### 1. Create Grafana Service Account

Create a service account in Grafana UI with Editor role for full read/write access:

**Steps**:
1. Open Grafana UI at `https://grafana.${ts_net}`
2. Navigate to: **Administration** → **Service Accounts**
3. Click **Add service account**
4. Configure:
   - **Display name**: `grafana-mcp-server`
   - **Role**: `Editor`
5. Click **Create**
6. Click **Add service account token**
7. Copy the generated token (it won't be shown again)

### 2. Create Sealed Secret

Replace `<your-token-from-grafana>` with the token from step 1:

```bash
kubectl create secret generic grafana-mcp-credentials \
  --namespace=monitoring \
  --from-literal=GRAFANA_SERVICE_ACCOUNT_TOKEN='<your-token-from-grafana>' \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > monitoring/controllers/grafana-mcp/grafana-mcp-credentials-sealed-secret.yaml
```

**Note**: The Grafana URL (`http://kube-prometheus-stack-grafana.monitoring.svc.cluster.local:80`) is configured directly in the HelmRelease as it is not sensitive information and is fixed for this cluster.

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
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | Sealed Secret | Service account token for authentication |

### Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| **Grafana URL** | `http://kube-prometheus-stack-grafana.monitoring.svc.cluster.local:80` | Internal Grafana service URL (configured in HelmRelease) |
| **Internal Service** | `grafana-mcp.monitoring.svc.cluster.local:8000/sse` | Cluster-internal SSE endpoint |
| **External Access** | `https://grafana-mcp.${ts_net}/sse` | Tailscale network SSE endpoint |

### Resources

| Resource | Request | Limit |
|----------|---------|-------|
| **CPU** | 100m | 500m |
| **Memory** | 256Mi | 512Mi |

### Grafana Service Account Permissions

**Editor Role** (Full Access):
- `datasources:*` - Read and query data sources
- `dashboards:*` - Read, create, and update dashboards
- `folders:*` - Read and create folders
- `teams:*` - Read teams
- `global.users:*` - Read users
- `alert.rules:*` - Manage alert rules
- `alert.notifications:*` - Manage notifications
- `annotations:*` - Read and write annotations
- `incidents:*` - Manage incidents

## MCP Client Configuration

This section covers 3 different configuration methods for connecting to the Grafana MCP server.

### Configuration 1: Inside the Cluster

**Use Case**: Workloads running inside the Kubernetes cluster (e.g., Coder devcontainers, ARC runners).

**Access Method**: Direct cluster service access via internal DNS

**MCP Client Configuration**:
```json
{
  "mcpServers": {
    "grafana": {
      "url": "http://grafana-mcp.monitoring.svc.cluster.local:8000/sse",
      "transport": "sse"
    }
  }
}
```

**Characteristics**:
- Low latency (service-to-service communication)
- No Tailscale required
- Uses internal Kubernetes DNS
- Available to all pods in the cluster

### Configuration 2: Outside via Tailscale Network

**Use Case**: External workloads connected to the Tailscale network (e.g., Codespaces with Tailscale, local PC with Tailscale).

**Access Method**: Tailscale ingress (private network overlay)

**MCP Client Configuration**:
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

**Prerequisites**:
- Tailscale client installed and authenticated
- Connected to the cluster's Tailscale network
- Access to `*.${ts_net}` domain

**Characteristics**:
- Secure access over Tailscale mesh network
- HTTPS with automatic TLS via Tailscale
- Can access from anywhere with Tailscale
- Private network (not exposed to public internet)

### Configuration 3: GitHub Copilot Coding Agent

**Use Case**: GitHub Copilot coding agent running in the cluster via Actions Runner Controller (ARC).

**Access Method**: Direct cluster service access via internal DNS

**Read-Only Configuration**: Configure read-only tools to prevent accidental modifications during troubleshooting.

**Setup Instructions**:

1. Navigate to your GitHub repository settings
2. Go to: **Copilot** → **MCP Servers**
3. Add the following configuration:

```json
{
  "mcpServers": {
    "grafana": {
      "url": "http://grafana-mcp.monitoring.svc.cluster.local:8000/sse",
      "transport": "sse",
      "tools": [
        "get_dashboard",
        "search_dashboards",
        "get_datasources",
        "prometheus_query",
        "prometheus_query_range",
        "prometheus_series",
        "prometheus_labels",
        "prometheus_label_values",
        "loki_query",
        "loki_query_range",
        "loki_series",
        "loki_labels",
        "loki_label_values",
        "tempo_search",
        "tempo_trace_by_id",
        "list_folders",
        "list_alert_rules",
        "list_alert_instances",
        "list_alert_contacts",
        "get_alert_rule",
        "list_incidents",
        "get_incident",
        "list_teams",
        "list_users"
      ]
    }
  }
}
```

**Read-Only Tools**:
The configuration above includes only read-only tools. The following write operations are excluded:
- `update_dashboard` - Dashboard modifications
- `create_folder` - Folder creation
- `create_incident`, `add_activity_to_incident` - Incident management
- `create_alert_rule`, `update_alert_rule`, `delete_alert_rule` - Alert rule modifications
- `create_annotation`, `update_annotation`, `patch_annotation` - Annotation modifications
- `find_error_pattern_logs`, `find_slow_requests` - Investigation creation (Sift tools)

**Characteristics**:
- Read-only access for safe troubleshooting
- Same internal DNS access as Configuration 1
- GitHub Copilot agent runs in `arc-runners` namespace
- Prevents accidental modifications during automated workflows
- Full observability data access for AI-assisted debugging

**References**:
- [GitHub Copilot Coding Agent with MCP](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/extend-coding-agent-with-mcp#writing-a-json-configuration-for-mcp-servers)
- [Grafana MCP Read-Only Mode](https://github.com/grafana/mcp-grafana/blob/main/README.md#read-only-mode)

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

### Get Dashboard

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

### Search Dashboards

```json
{
  "method": "tools/call",
  "params": {
    "name": "search_dashboards",
    "arguments": {
      "query": "kubernetes"
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
curl -N https://grafana-mcp.${ts_net}/sse
```

Expected: SSE event stream (connection stays open)

### 4. Test from Inside Cluster

```bash
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl -N http://grafana-mcp.monitoring.svc.cluster.local:8000/sse
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

To update the Grafana URL or other settings:

1. Edit `monitoring/controllers/grafana-mcp/release.yaml`
2. Commit and push
3. Flux will reconcile within 1 hour (or force: `flux reconcile hr grafana-mcp -n monitoring`)

To update the service account token:

1. Regenerate sealed secret with new token
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
2. Ensure service account has Editor role
3. Regenerate token and update sealed secret

### Connection Timeout

**Symptom**: Cannot reach Grafana from MCP server

**Causes**:
1. Incorrect Grafana URL in release.yaml
2. Network policy blocking traffic
3. Grafana service not ready

**Resolution**:
1. Test connectivity from pod:
   ```bash
   kubectl exec -it -n monitoring <grafana-mcp-pod> -- sh
   # Inside pod:
   wget -O- http://kube-prometheus-stack-grafana.monitoring.svc.cluster.local:80/api/health
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

**Troubleshooting by Configuration**:

**Configuration 1 & 3 (In-Cluster)**:
```bash
# Verify service is accessible
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl -v http://grafana-mcp.monitoring.svc.cluster.local:8000/sse
```

**Configuration 2 (Tailscale)**:
```bash
# Verify Tailscale connection
tailscale status

# Test endpoint
curl -v https://grafana-mcp.${ts_net}/sse
```

## References

- [Grafana MCP GitHub Repository](https://github.com/grafana/mcp-grafana)
- [Grafana MCP Docker Image](https://hub.docker.com/r/grafana/mcp-grafana)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Grafana Service Accounts Documentation](https://grafana.com/docs/grafana/latest/administration/service-accounts/)
- [Grafana Helm Charts](https://github.com/grafana/helm-charts)
- [Flux HelmRelease Documentation](https://fluxcd.io/docs/components/helm/helmreleases/)
- [GitHub Copilot Coding Agent with MCP](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/extend-coding-agent-with-mcp)

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
- Use read-only tool configuration for GitHub Copilot agent to prevent accidental modifications
- Audit logs available in Grafana for API access tracking
