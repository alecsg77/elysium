# Elasticsearch MCP Server

This directory contains the configuration for the [Elasticsearch MCP Server](https://github.com/elastic/mcp-server-elasticsearch), which provides Model Context Protocol access to Elasticsearch data.

## Overview

The Elasticsearch MCP Server allows AI agents to interact with Elasticsearch indices through natural language conversations using the Model Context Protocol (MCP).

**⚠️ Note**: The Elasticsearch MCP Server is deprecated by upstream and will only receive critical security updates. It has been superseded by [Elastic Agent Builder](https://ela.st/agent-builder-docs)'s [MCP endpoint](https://ela.st/agent-builder-mcp), available in Elastic 9.2.0+ and Elasticsearch Serverless projects.

## Architecture

- **Chart**: OneChart (generic Helm chart)
- **Image**: `docker.elastic.co/mcp/elasticsearch:latest`
- **Protocol**: Streamable HTTP (recommended over deprecated SSE)
- **Endpoint**: `http://elasticsearch-mcp.monitoring.svc.cluster.local:8080/mcp`
- **Health Check**: `http://elasticsearch-mcp.monitoring.svc.cluster.local:8080/ping`
- **Ingress**: Tailscale (`elasticsearch-mcp` hostname)
- **Elasticsearch**: Connects to `https://elasticsearch-es-http.monitoring.svc.cluster.local:9200`

## Available Tools

The MCP server provides the following tools to AI agents:

- `list_indices`: List all available Elasticsearch indices
- `get_mappings`: Get field mappings for a specific index
- `search`: Perform Elasticsearch search with query DSL
- `esql`: Perform ES|QL queries
- `get_shards`: Get shard information for indices

## Configuration

### Environment Variables

The server is configured through environment variables in the sealed secret:

#### Authentication (choose one method):

**API Key (Recommended)**:
```bash
ES_API_KEY: <elasticsearch-api-key>
```

**Basic Authentication**:
```bash
ES_USERNAME: <elasticsearch-username>
ES_PASSWORD: <elasticsearch-password>
```

#### Optional Configuration:

```bash
ES_SSL_SKIP_VERIFY: "true"  # Skip SSL/TLS certificate verification (not recommended for production)
```

### Elasticsearch Connection

The server connects to the Elasticsearch instance deployed in the monitoring namespace:
- URL: `https://elasticsearch-es-http.monitoring.svc.cluster.local:9200`
- Certificate: Uses the Elasticsearch cluster's self-signed certificate

## Setup Instructions

### 1. Create Elasticsearch API Key

First, create an API key in Elasticsearch. You can do this by port-forwarding to Elasticsearch and using curl:

```bash
# Port-forward to Elasticsearch
kubectl port-forward -n monitoring svc/elasticsearch-es-http 9200:9200

# Get the elastic user password
kubectl get secret elasticsearch-es-elastic-user -n monitoring -o jsonpath='{.data.elastic}' | base64 -d

# Create API key (in another terminal)
curl -X POST "https://localhost:9200/_security/api_key" \
  -k -u "elastic:<password-from-above>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "elasticsearch-mcp-server",
    "role_descriptors": {
      "mcp_server_role": {
        "cluster": ["monitor", "manage_index_templates"],
        "indices": [
          {
            "names": ["*"],
            "privileges": ["read", "view_index_metadata"]
          }
        ]
      }
    }
  }'
```

This will return an API key in the format: `<id>:<api_key>`

### 2. Create Sealed Secret

Use the following command to create the sealed secret with the API key:

#### Using API Key (Recommended):

```bash
# Create the secret with API key
kubectl create secret generic elasticsearch-mcp-credentials \
  --namespace=monitoring \
  --from-literal=ES_API_KEY='<api-key-from-step-1>' \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > monitoring/controllers/elasticsearch-mcp/elasticsearch-mcp-credentials-sealed-secret.yaml
```

#### Using Basic Authentication (Alternative):

```bash
# Get the elastic user password
ES_PASSWORD=$(kubectl get secret elasticsearch-es-elastic-user -n monitoring -o jsonpath='{.data.elastic}' | base64 -d)

# Create the secret with username and password
kubectl create secret generic elasticsearch-mcp-credentials \
  --namespace=monitoring \
  --from-literal=ES_USERNAME='elastic' \
  --from-literal=ES_PASSWORD="${ES_PASSWORD}" \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > monitoring/controllers/elasticsearch-mcp/elasticsearch-mcp-credentials-sealed-secret.yaml
```

#### Optional: Skip SSL Verification

If you need to skip SSL verification (not recommended for production):

```bash
# Add ES_SSL_SKIP_VERIFY to existing secret creation
kubectl create secret generic elasticsearch-mcp-credentials \
  --namespace=monitoring \
  --from-literal=ES_API_KEY='<api-key>' \
  --from-literal=ES_SSL_SKIP_VERIFY='true' \
  --dry-run=client -o yaml | \
  kubeseal --cert etc/certs/pub-sealed-secrets.pem \
  --format=yaml > monitoring/controllers/elasticsearch-mcp/elasticsearch-mcp-credentials-sealed-secret.yaml
```

### 3. Deploy

Once the sealed secret is created, commit and push the changes. Flux will automatically reconcile and deploy the MCP server.

```bash
git add monitoring/controllers/elasticsearch-mcp/
git commit -m "feat(monitoring): add elasticsearch-mcp server"
git push
```

### 4. Verify Deployment

```bash
# Check deployment status
kubectl get pods -n monitoring -l app=elasticsearch-mcp

# Check service
kubectl get svc -n monitoring elasticsearch-mcp

# Check ingress
kubectl get ingress -n monitoring elasticsearch-mcp

# Test health endpoint
kubectl exec -n monitoring deploy/elasticsearch-mcp -- curl -s http://localhost:8080/ping

# Check logs
kubectl logs -n monitoring -l app=elasticsearch-mcp -f
```

## Client Configuration

### Claude Desktop (via mcp-proxy)

For Claude Desktop (which only supports stdio), use `mcp-proxy` to bridge stdio to streamable-http:

```json
{
  "mcpServers": {
    "elasticsearch-mcp-server": {
      "command": "/home/<user>/.local/bin/mcp-proxy",
      "args": [
        "--transport=streamablehttp",
        "http://elasticsearch-mcp.monitoring.ts.net/mcp"
      ]
    }
  }
}
```

### Direct Streamable HTTP

For clients that support streamable-HTTP directly:

```json
{
  "mcpServers": {
    "elasticsearch-mcp-server": {
      "url": "http://elasticsearch-mcp.monitoring.ts.net/mcp",
      "transport": "streamable-http"
    }
  }
}
```

## Troubleshooting

### Connection Issues

If the server can't connect to Elasticsearch:

1. Check Elasticsearch is running:
   ```bash
   kubectl get elasticsearch -n monitoring
   ```

2. Verify the service endpoint:
   ```bash
   kubectl get svc -n monitoring elasticsearch-es-http
   ```

3. Test connectivity from a pod:
   ```bash
   kubectl run -n monitoring curl-test --rm -it --image=curlimages/curl -- \
     curl -k https://elasticsearch-es-http.monitoring.svc.cluster.local:9200
   ```

### Authentication Issues

If you see authentication errors:

1. Verify the API key or credentials are correct
2. Check the sealed secret was properly created:
   ```bash
   kubectl get secret -n monitoring elasticsearch-mcp-credentials -o yaml
   ```

3. Test credentials manually:
   ```bash
   # Get the unsealed credentials
   ES_API_KEY=$(kubectl get secret -n monitoring elasticsearch-mcp-credentials -o jsonpath='{.data.ES_API_KEY}' | base64 -d)
   
   # Test with curl
   kubectl port-forward -n monitoring svc/elasticsearch-es-http 9200:9200
   curl -k -H "Authorization: ApiKey ${ES_API_KEY}" https://localhost:9200/
   ```

### SSL/TLS Certificate Issues

If you see certificate verification errors:

1. The Elasticsearch cluster uses a self-signed certificate
2. You may need to set `ES_SSL_SKIP_VERIFY: "true"` in the sealed secret
3. Or configure the server to trust the Elasticsearch CA certificate

## Resources

- [Elasticsearch MCP Server GitHub](https://github.com/elastic/mcp-server-elasticsearch)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Elasticsearch API Key Management](https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-create-api-key.html)
- [Elastic Agent Builder MCP](https://ela.st/agent-builder-mcp) (successor to this server)

## Security Considerations

- **API Keys**: Use API keys with minimal required permissions
- **Network**: Access is restricted via Tailscale ingress
- **SSL/TLS**: Consider proper certificate management instead of skipping verification
- **Credentials**: Never commit plain text credentials; always use sealed secrets
