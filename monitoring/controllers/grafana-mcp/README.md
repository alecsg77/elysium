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
- **Access**: Private native-HTTPS endpoint at `https://grafana-mcp.${PRIVATE_DOMAIN}/mcp`, reached through Tailnet Service-CIDR routes
- **Port**: 443 externally, forwarded by `grafana-mcp-https` to the chart's native Streamable HTTP port 8000
- **Protocol**: MCP 2025-06-18 (backward compatible with 2024-11-05)

## Prerequisites

### 1. Create Grafana Service Account

Create a service account in Grafana UI with Editor role for full read/write access:

**Steps**:
1. Open Grafana UI at `https://grafana.${PRIVATE_DOMAIN}`
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

**Note**: The Grafana URL (`https://grafana.${PRIVATE_DOMAIN}`) is configured directly in the HelmRelease as it is not sensitive information and is fixed for this cluster.

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
| **Grafana URL** | `https://grafana.${PRIVATE_DOMAIN}` | Native-HTTPS Grafana endpoint configured in the HelmRelease |
| **MCP endpoint** | `https://grafana-mcp.${PRIVATE_DOMAIN}/mcp` | Native-HTTPS endpoint for all MCP clients; preserves certificate SNI |
| **Cluster Service** | `grafana-mcp-https.monitoring.svc.cluster.local:443/mcp` | Optional in-cluster path when its client can validate the external certificate hostname |

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

**Transport Mode**: The server is explicitly configured with **Streamable HTTP** transport via the `-t streamable-http` flag (MCP protocol 2025-06-18). This provides native support for modern MCP clients:
- **Modern clients** (VSCode, Claude Desktop): Use `"type": "http"` - supports both POST and GET on `/mcp` endpoint
- **Protocol support**: Full implementation of MCP 2025-06-18 Streamable HTTP specification
- **Backward compatibility**: The Streamable HTTP transport automatically handles legacy protocol fallback when needed

Clients should use `"type": "http"` (not `"sse"`) as this is the Streamable HTTP transport mode.

### Configuration 1: VS Code project configuration

**Use Case**: VS Code clients running locally or from a Coder workspace.

**Access Method**: Private DNS endpoint with native TLS. Set `PRIVATE_DOMAIN` in the local VS Code environment; the checked-in `.vscode/mcp.json` uses this environment variable so the real private suffix is not committed.

**MCP Client Configuration**:
```json
{
  "mcpServers": {
    "grafana": {
      "url": "https://grafana-mcp.${env:PRIVATE_DOMAIN}/mcp",
      "type": "http"
    }
  }
}
```

**Characteristics**:
- Uses the certificate's externally named hostname, preserving TLS SNI validation.
- Reaches the Service ClusterIP over existing Tailnet Service-CIDR routes.
- Does not require a Tailscale Ingress or a reverse proxy TLS terminator.

### Mux configuration

Mux does not interpolate environment-variable placeholders in HTTP MCP URLs. Configure Grafana in each user's untracked global `~/.mux/mcp.jsonc` with the literal private endpoint; do not place the real private domain in this repository:

```jsonc
{
  "servers": {
    "grafana": {
      "transport": "http",
      "url": "https://grafana-mcp.<private-domain>/mcp"
    }
  }
}
```

The tracked `.mux/mcp.jsonc` intentionally omits this server while retaining the portable Kubernetes and Flux entries.

### Configuration 2: Other Tailnet-connected clients

**Use Case**: External workloads connected to the Tailnet (for example, a local workstation or Codespaces with Tailscale).

**Access Method**: The same private DNS endpoint with native TLS

**MCP Client Configuration**:
```json
{
  "mcpServers": {
    "grafana": {
      "url": "https://grafana-mcp.${PRIVATE_DOMAIN}/mcp",
      "type": "http"
    }
  }
}
```

**Prerequisites**:
- Tailscale client installed and authenticated.
- Connected to the Tailnet with the Service-CIDR route available.
- DNS resolution for `${PRIVATE_DOMAIN}`.

**Characteristics**:
- Secure transport over the Tailnet plus TLS terminated by the MCP workload.
- The DNS record is private/DNS-only; this endpoint is not public Internet exposure.
- Client configuration is identical to Configuration 1.

### Configuration 3: GitHub Copilot Coding Agent

**Use Case**: GitHub Copilot coding agent running in the cluster via Actions Runner Controller (ARC).

**Access Method**: The same private DNS endpoint with native TLS

**Read-Only Configuration**: Configure read-only tools to prevent accidental modifications during troubleshooting.

**Setup Instructions**:

1. Navigate to your GitHub repository settings
2. Go to: **Copilot** → **MCP Servers**
3. Add the following configuration:

```json
{
  "mcpServers": {
    "grafana": {
      "url": "https://grafana-mcp.${PRIVATE_DOMAIN}/mcp",
      "type": "http",
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
- Uses the same private DNS/TLS endpoint as Configuration 1
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
curl -N https://grafana-mcp.${PRIVATE_DOMAIN}/mcp
```

Expected: SSE event stream (connection stays open)

### 4. Test from Inside Cluster

```bash
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl -N https://grafana-mcp.${PRIVATE_DOMAIN}/mcp
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
   wget -O- https://grafana.${PRIVATE_DOMAIN}/api/health
   ```
2. Check Grafana service exists:
   ```bash
   kubectl get svc -n monitoring kube-prometheus-stack-grafana
   ```

### Native HTTPS Endpoint Not Working

**Symptom**: Cannot access `https://grafana-mcp.${PRIVATE_DOMAIN}`

**Causes**:
1. Certificate has not become ready or is not mounted by the pod.
2. ExternalDNS has not published the Service record.
3. The Tailscale Connector Service-CIDR route is unavailable.

**Resolution**:
1. Check certificate and the generated Secret:
   ```bash
   kubectl get certificate,secret -n monitoring monitoring-wildcard-tls
   ```
2. Check the ExternalDNS-facing Service and its endpoints:
   ```bash
   kubectl get svc,endpoints -n monitoring grafana-mcp-https
   ```
3. Check the Tailnet route and DNS response from the client:
   ```bash
   tailscale status
   ```

### MCP Client Connection Issues

**Symptom**: MCP client cannot connect to server

**Troubleshooting by Configuration**:

**Configurations 1, 2, and 3 (native HTTPS endpoint)**:
```bash
# Verify service is accessible
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl -v https://grafana-mcp.${PRIVATE_DOMAIN}/mcp
```

```bash
# Verify the Tailnet connection and test the shared endpoint.
tailscale status
curl -v https://grafana-mcp.${PRIVATE_DOMAIN}/mcp
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
