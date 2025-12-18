# Secure Troubleshooting

Guidelines for handling sensitive information during cluster troubleshooting and diagnostics.

## Core Principle

**All troubleshooting artifacts must be treated as sensitive until proven otherwise.**

## Before Sharing Diagnostics

### Mandatory Pre-Share Steps

1. **Limit log output**: Paste only the exact lines demonstrating the failure
2. **Summarize verbosity**: Reference where full output can be pulled rather than posting it all
3. **Replace sensitive data**: Use meaningful placeholders for:
   - Secrets and tokens
   - Hostnames and IP addresses
   - File paths and volume IDs
   - Usernames and email addresses
4. **Document redactions**: Note every redaction so future responders understand gaps
5. **Rotate if leaked**: Request credential rotation immediately if something was exposed

### Redaction Guidelines

#### What to Redact

| Data Type | Example | Placeholder |
|-----------|---------|-------------|
| **Tokens** | `ghp_abc123...` | `[REDACTED_GITHUB_TOKEN]` |
| **Passwords** | `password: secret123` | `password: [REDACTED]` |
| **API Keys** | `apiKey: sk-proj-...` | `apiKey: [REDACTED_API_KEY]` |
| **IP Addresses** | `10.43.5.12` | `<AI_NAMESPACE_NODE_IP>` |
| **Hostnames** | `server.internal.local` | `<INTERNAL_SERVER>` |
| **Volume IDs** | `pvc-abc123-def456` | `<MONGODB_PVC_ID>` |
| **File Paths** | `/home/user/.ssh/id_rsa` | `<SSH_KEY_PATH>` |
| **Usernames** | `admin@example.com` | `<ADMIN_USER>` |

#### What NOT to Share

❌ **Never post**:
- Output of `kubectl describe secret`
- Kubeconfig files (contain credentials)
- Credential JSON files
- Base64-decoded Secret data
- Private keys or certificates
- OAuth tokens or bearer tokens
- Database connection strings with credentials

✅ **Instead, state**:
- "Secret `app-secret` is missing key `api-key`"
- "Kubeconfig authentication failed"
- "SealedSecret `db-creds` not decrypting"

## Mandatory Security Scan

Run this scan over any diagnostic directory before sharing content:

### Using ripgrep (Recommended)

```bash
# From repo root, scan for high-risk terms
rg -n --no-heading -e 'password|secret|token|apikey|bearer|session|private key' \
  diagnostics/ logs/ tmp/ 2>/dev/null

# Detect stray key or certificate blocks
rg -n --no-heading -e 'BEGIN RSA PRIVATE KEY|BEGIN OPENSSH PRIVATE KEY|BEGIN CERTIFICATE' \
  diagnostics/ logs/ tmp/ 2>/dev/null
```

### Using grep (Portable Alternative)

```bash
# Portable alternative when ripgrep is unavailable
grep -RIn --color=never -E 'password|secret|token|apikey|bearer' \
  diagnostics/ logs/ tmp/
```

### Scan Workflow

1. Run scan command
2. Review matches carefully
3. Redact all sensitive matches
4. Rerun scan to verify clean
5. Only then share diagnostics

## Redaction Workflow

### Step 1: Collect Diagnostics

```bash
# Create diagnostic directory
mkdir -p diagnostics

# Collect safe diagnostics
kubectl get all -n <namespace> > diagnostics/resources.txt
kubectl get events -n <namespace> --sort-by='.lastTimestamp' > diagnostics/events.txt
flux get all -A > diagnostics/flux-status.txt

# Collect logs (may contain sensitive data)
kubectl logs -n <namespace> <pod> --tail=100 > diagnostics/pod-logs.txt
```

### Step 2: Scan for Sensitive Data

```bash
# Run security scan
rg -n 'password|secret|token|apikey' diagnostics/
```

### Step 3: Redact Matches

Open each file with matches and replace sensitive values:

```diff
# Before
- apiKey: sk-proj-abc123def456
- token: ghp_secrettoken123

# After
+ apiKey: [REDACTED_API_KEY]
+ token: [REDACTED_GITHUB_TOKEN]
```

### Step 4: Add Redaction Notes

Document what was redacted:

```
[REDACTION NOTE: GitHub token value redacted from line 42]
[REDACTION NOTE: Database password redacted; see event at 2025-12-18T10:00Z for auth failure]
```

### Step 5: Verify Clean

```bash
# Rerun security scan
rg -n 'password|secret|token|apikey' diagnostics/

# Should return no matches (or only your redaction placeholders)
```

### Step 6: Share Safely

Now diagnostics are safe to share in:
- GitHub Issues
- Pull Request comments
- Chat discussions
- Documentation

## Post-Incident Review

After resolving an issue:

### 1. Audit Shared Artifacts

```bash
# Re-scan all evidence gathered during fix
rg -n 'password|secret|token|apikey' diagnostics/ logs/ tmp/

# Check Git history for sensitive commits
git log --all --oneline | grep -i 'secret\|password\|token'

# Check issue/PR comments
# Review manually in GitHub UI
```

### 2. Verify PR Diffs

Ensure merged PR contains only intentional configuration:
- ✅ Resource definitions
- ✅ Configuration values
- ✅ Version updates
- ❌ Debug dumps
- ❌ Log pastes
- ❌ Secret literals

### 3. Rotate Exposed Credentials

If any credential might have been exposed:

```bash
# Rotate sealed-secrets
# Create new SealedSecret with new value
kubeseal < new-secret.yaml > sealed-secret.yaml

# Update in Git
git add sealed-secret.yaml
git commit -m "chore(security): rotate exposed credential"
git push

# Document rotation
# Add comment to issue: "Rotated [credential-type] after exposure"
```

### 4. Clean Up Artifacts

```bash
# Remove diagnostic directories
rm -rf diagnostics/ logs/ tmp/

# Add to .gitignore if not already present
echo "diagnostics/" >> .gitignore
echo "logs/" >> .gitignore
echo "tmp/" >> .gitignore
```

### 5. Document in Knowledge Base

If leak was discovered after the fact:
1. Open dedicated security issue
2. Coordinate cleanup (log purges, Git history rewrites, access revocations)
3. Document in `/docs/security/incidents/` (if severe)
4. Update runbooks with preventive measures

## Safe Diagnostic Commands

These commands are generally safe to share output:

### Cluster Status (Safe)

```bash
# Flux status
flux get all -A

# Resource status
kubectl get all -A
kubectl get kustomizations -A
kubectl get hr -A

# Events (may need redaction)
kubectl get events -A --sort-by='.lastTimestamp'

# Node status
kubectl get nodes
kubectl top nodes
```

### Resource Details (Redact Required)

```bash
# Describe resources (may contain secrets)
kubectl describe pod <name> -n <namespace>  # Check env vars
kubectl describe hr <name> -n <namespace>   # Check values

# Configuration (may contain secrets)
kubectl get cm <name> -n <namespace> -o yaml  # Redact sensitive values
```

### Logs (Redact Required)

```bash
# Pod logs (often contain sensitive data)
kubectl logs -n <namespace> <pod> --tail=100  # Redact tokens, passwords

# Controller logs (may contain secret names)
kubectl logs -n flux-system deploy/helm-controller --tail=100
```

## Redaction Examples

### Example 1: Pod Logs

**Before**:
```
2025-12-18T10:00:00Z INFO Connecting to database: postgresql://admin:secret123@db.internal:5432/myapp
2025-12-18T10:00:01Z ERROR Failed to authenticate with API key: sk-proj-abc123def456
```

**After**:
```
2025-12-18T10:00:00Z INFO Connecting to database: postgresql://[REDACTED_DB_USER]:[REDACTED_DB_PASS]@<DB_HOST>:5432/myapp
2025-12-18T10:00:01Z ERROR Failed to authenticate with API key: [REDACTED_API_KEY]

[REDACTION NOTE: Database credentials and API key redacted from connection logs]
```

### Example 2: HelmRelease Values

**Before**:
```yaml
spec:
  values:
    database:
      host: db.internal.local
      username: admin
      password: MyS3cr3tP@ss
    api:
      token: ghp_secrettoken123
```

**After**:
```yaml
spec:
  values:
    database:
      host: <DB_HOST>
      username: <DB_USER>
      password: [REDACTED_DB_PASSWORD]
    api:
      token: [REDACTED_GITHUB_TOKEN]

[REDACTION NOTE: Database credentials and GitHub token redacted]
```

### Example 3: Event Logs

**Before**:
```
10m   Warning   FailedMount   Pod/myapp-123   MountVolume.SetUp failed: rpc error: code = Unknown desc = failed to mount: exit status 1: mount.azure: connection string contains secret
```

**After**:
```
10m   Warning   FailedMount   Pod/myapp-123   MountVolume.SetUp failed: rpc error: code = Unknown desc = failed to mount: exit status 1: mount.azure: connection string contains [REDACTED_CONNECTION_STRING]

[REDACTION NOTE: Azure connection string redacted from mount error]
```

## Best Practices Checklist

Before sharing diagnostics:
- [ ] Limited to relevant lines only
- [ ] Scanned for sensitive terms
- [ ] All secrets/tokens redacted
- [ ] IP addresses replaced with placeholders
- [ ] Hostnames generalized
- [ ] File paths sanitized
- [ ] Redactions documented
- [ ] Scan rerun to verify clean

During troubleshooting:
- [ ] Don't make manual cluster changes while investigating
- [ ] Document what was tested
- [ ] Keep diagnostics local (don't commit)
- [ ] Clean up after resolution

Post-resolution:
- [ ] Re-scan all shared artifacts
- [ ] Verify PR diffs are clean
- [ ] Rotate exposed credentials
- [ ] Delete diagnostic directories
- [ ] Update knowledge base

## Emergency Response

If sensitive data was exposed:

### Immediate Actions (< 1 hour)

1. **Identify scope**: What was exposed and where?
2. **Rotate credentials**: Change all potentially exposed secrets
3. **Notify stakeholders**: Alert team of exposure
4. **Remove artifacts**: Delete exposed data from issues/PRs/chat

### Short-term Actions (< 24 hours)

1. **Update SealedSecrets**: Create new sealed secrets with rotated values
2. **Review access logs**: Check if exposed credentials were used
3. **Document incident**: Create security incident report
4. **Update procedures**: Add preventive measures to runbooks

### Long-term Actions (< 1 week)

1. **Git history cleanup**: Rewrite history if secrets committed (coordinate with team)
2. **Access review**: Verify no unauthorized access occurred
3. **Process improvement**: Update documentation and training
4. **Post-mortem**: Conduct blameless post-mortem

## Related Documentation

- [Secret Management Guide](/docs/security/secret-management.md)
- [Web-Based Troubleshooting](/docs/troubleshooting/web-troubleshooting.md)
- [Known Issues](/docs/troubleshooting/known-issues.md)
- [Repository Structure Standards](/docs/standards/repository-structure.md)
