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
- **Access**: Cluster-internal HTTP Service endpoint only: `http://grafana-mcp.monitoring.svc:8000/mcp`
- **Port**: 8000 (Streamable HTTP transport)
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
| **MCP endpoint** | `http://grafana-mcp.monitoring.svc:8000/mcp` | Cluster-internal HTTP Service endpoint for MCP clients |
| **Allowed HTTP Host** | `grafana-mcp.monitoring.svc:8000` | Exact Host header accepted by the server; no wildcard or external hostname is configured |
| **Exposure** | None | No ExternalDNS Service and no Tailscale Ingress are created for Grafana MCP |

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

### Configuration 1: VS Code and Mux project configuration

**Use Case**: Clients running inside the Kubernetes cluster, including Coder workspaces and ARC runners.

**Access Method**: Direct cluster Service access. The tracked `.vscode/mcp.json` and `.mux/mcp.jsonc` both use this endpoint:

```text
http://grafana-mcp.monitoring.svc:8000/mcp
```

**Characteristics**:
- No ExternalDNS record, private DNS name, certificate, or Tailscale Ingress is used for Grafana MCP.
- The endpoint is reachable only from workloads that can resolve and reach the cluster Service network.
- External Tailnet clients cannot access Grafana MCP directly.

### Configuration 3: GitHub Copilot Coding Agent

**Use Case**: GitHub Copilot coding agent running in the cluster via Actions Runner Controller (ARC).

**Access Method**: Direct cluster Service access over HTTP

**Read-Only Configuration**: Configure read-only tools to prevent accidental modifications during troubleshooting.

**Setup Instructions**:

1. Navigate to your GitHub repository settings
2. Go to: **Copilot** → **MCP Servers**
3. Add the following configuration:

```json
{
  "mcpServers": {
    "grafana": {
      "url": "http://grafana-mcp.monitoring.svc:8000/mcp",
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

### 3. Test the cluster Service endpoint and Host allowlist

```bash
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl -fsS http://grafana-mcp.monitoring.svc:8000/healthz
```

Expected: a successful health response, not `403 forbidden: host not allowed`. The request must use the exact Service hostname above; do not override the Host header or use an external hostname.

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

## Maintenance

### Token Rotation

Rotate the service account token periodically (quarterly recommended) through GitOps only:

1. Generate a new token in Grafana UI (Service Accounts → grafana-mcp-server → Tokens).
2. Regenerate `grafana-mcp-credentials-sealed-secret.yaml` with the new token; do not commit a plaintext Secret.
3. Calculate the non-secret SHA-256 of the sealed manifest, encode it as eight hyphen-separated hexadecimal groups prefixed by `sha256`, and update `podAnnotations.checksum/grafana-mcp-credentials` in `release.yaml` to that value:
   ```bash
   sha256sum monitoring/controllers/grafana-mcp/grafana-mcp-credentials-sealed-secret.yaml | \
     awk '{printf "sha256"; for (i = 1; i <= length($1); i += 8) printf "-%s", substr($1, i, 8); print ""}'
   ```
4. Commit and push both files. Flux applies the Secret update and the changed pod-template annotation creates a new Grafana MCP pod, which reads the token through `envFrom` at startup.

Do not use `kubectl rollout restart`, patch the Deployment, or reconcile resources directly for this GitOps-managed workload. To roll back a token rotation, revert both the SealedSecret and its checksum annotation in Git.

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
3. Let Flux reconcile on its configured interval; do not reconcile the HelmRelease directly.

To update the service account token, follow **Token Rotation** above so the sealed manifest and pod-template checksum change together.

## Troubleshooting

### Pod Not Starting

**Symptom**: Pod in `CrashLoopBackOff` or `Error` state

**Common Causes**:
1. **Missing/invalid token**: Confirm that the generated Secret exists without displaying its data
   ```bash
   kubectl describe secret grafana-mcp-credentials -n monitoring
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

### Cluster Service Endpoint Not Working

**Symptom**: A workload cannot access `http://grafana-mcp.monitoring.svc:8000/mcp`.

**Causes**:
1. The Grafana MCP pod is not ready.
2. The chart-managed Service has no ready endpoints.
3. The request Host does not exactly match `grafana-mcp.monitoring.svc:8000`.
4. The client is outside the cluster network or cannot resolve cluster DNS.

**Resolution**:
1. Check the Service and its endpoints:
   ```bash
   kubectl get svc,endpoints -n monitoring grafana-mcp
   ```
2. Check the workload's logs and readiness:
   ```bash
   kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana-mcp
   ```
3. Run the in-cluster request from the validation step above. Do not use a Tailnet hostname: no external endpoint is created.

### MCP Client Connection Issues

**Symptom**: MCP client cannot connect to server

**Troubleshooting by Configuration**:

**Cluster Service clients**:
```bash
# Verify service discovery and HTTP connectivity from inside the cluster.
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl -v http://grafana-mcp.monitoring.svc:8000/mcp
```

Clients outside the cluster network are intentionally unsupported; no Tailnet or private-DNS endpoint is provisioned.

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
