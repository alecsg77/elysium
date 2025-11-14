---
agent: 'agent'
model: Claude Sonnet 4.5
tools: ['fetch', 'githubRepo', 'github/github-mcp-server/assign_copilot_to_issue']
description: 'Format and submit token-optimized resolution requests to GitHub coding agent'
---

# Request Resolution from GitHub Coding Agent

You are preparing a resolution request to submit to GitHub's Copilot coding agent for implementation.

## Objective

Create a **token-optimized request** that provides sufficient context for the coding agent to:
1. Understand the root cause
2. Implement the correct fix
3. Follow GitOps and security best practices
4. Validate the solution

## Token Budget

GitHub coding agent has limited context window. Optimize for:
- **Maximum**: 3000 tokens (~2000 characters)
- **Target**: 1500-2000 tokens for best results
- **Minimum**: Critical info only if must stay under 1000 tokens

## Request Structure

### Required Sections

#### 1. Issue Context (150-300 chars)
```
Bug: #[issue-number]
Component: [flux/kubernetes/helm/app]
Severity: [critical/high/medium/low]
Parent Investigation: #[parent-issue]
```

#### 2. Root Cause (200-400 chars)
**Compact, technical explanation**:
```
Root Cause: [2-3 sentence technical explanation]

Example:
Root Cause: HelmRelease for Ollama times out during installation because the default 5-minute timeout is insufficient for pulling the 8.2GB container image. Chart takes approximately 8 minutes to complete on current network.
```

#### 3. Error Context (500-2000 chars)
**Semantically complete error information**:

Include:
- ✅ Full error message
- ✅ Relevant stack trace (if applicable)
- ✅ Resource status conditions
- ✅ Key log lines

Exclude:
- ❌ Repeated errors
- ❌ Debug/info logs
- ❌ Timestamps (keep one for reference)
- ❌ Full resource YAML dumps

**Format**:
````markdown
Error:
```
[Semantically complete error - full message + essential context]
```

Resource Status:
- Kustomization/HelmRelease: [name]
- Namespace: [namespace]
- Condition: [current condition]
- Message: [status message]
````

**Example**:
````markdown
Error:
```
HelmRelease/ollama.ai Health check failed after timeout
Status: 'False'
Reason: InstallFailed
Message: install retries exhausted
Last Attempted: v1.2.3 (chart version)
```

Pod Status:
- ollama-xyz: ImagePullBackOff
- Init container: Pulling image (8.2GB)
- Event: "Back-off pulling image" (repeated 15 times)
````

#### 4. Current Configuration Excerpt (200-500 chars)
**Relevant portion only**:

Show:
- ✅ Section with problem
- ✅ Surrounding context (2-3 lines before/after)
- ✅ File path

**Example**:
```yaml
# apps/base/ai/ollama.yaml (lines 15-25)
spec:
  interval: 12h
  timeout: 5m  # ← Problem: Too short
  chart:
    spec:
      chart: ollama
      version: "1.2.3"
```

#### 5. Required Changes (300-600 chars)
**Specific, actionable modifications**:

Format:
```markdown
Changes:

1. File: `apps/base/ai/ollama.yaml`
   - Line ~20: Change `timeout: 5m` to `timeout: 15m`
   - Reason: Allow sufficient time for 8.2GB image pull

2. File: [additional if needed]
   [...]
```

**Be specific**:
- ❌ "Fix the timeout"
- ✅ "Change timeout from 5m to 15m on line 20"

#### 6. GitOps Constraints (200-400 chars)
**Critical requirements**:

```markdown
Constraints:
- ✅ GitOps workflow: Commit to Git, no kubectl apply
- ✅ Sealed Secrets: Use etc/certs/pub-sealed-secrets.pem for encryption
- ✅ Flux dependencies: [list if relevant]
- ✅ Conventional commits: type(scope): description
- ✅ Validate: kustomize build before commit

[If secrets needed]:
- Secret creation: Use kubeseal with provided cert
- Secret namespace: [must match resource namespace]
```

#### 7. Acceptance Criteria (150-300 chars)
**Clear validation steps**:

```markdown
Success Criteria:
- [ ] Flux reconciliation: flux get hr ollama -n ai shows Ready=True
- [ ] Pod status: ollama-xyz Running 1/1
- [ ] No errors in: kubectl get events -n ai
- [ ] Application healthy: [specific check if applicable]
```

#### 8. Validation Timing (50-100 chars)
**For automatic validation**:

```markdown
Auto-validation (10min timeout):
- Resource: HelmRelease/ollama
- Namespace: ai
- Expected state: Ready=True, pods Running
```

#### 9. Reference Links (100-150 chars)
**Where to find full context**:

```markdown
Full Context:
- Root cause analysis: #[parent-issue-number] (comment [link])
- Diagnostic reports: #[parent-issue-number] (comments)
- Resolution plan: #[bug-issue-number] (comment [link])
```

## Token Optimization Techniques

### Technique 1: Semantic Completeness
**Keep essential meaning, remove verbosity**:

❌ **Verbose** (800 chars):
```
The HelmRelease named "ollama" which is located in the "ai" namespace and is managed by Flux CD is currently experiencing a timeout issue during the installation process. The timeout is currently set to a value of 5 minutes as specified in the spec.timeout field of the HelmRelease resource manifest. However, the actual installation process requires more time than this because it needs to pull a very large container image that is 8.2 gigabytes in size from the registry, and this process takes approximately 8 minutes to complete on the current network connection speed.
```

✅ **Semantic** (200 chars):
```
HelmRelease ollama (namespace: ai) times out at 5m during install. Root cause: 8.2GB container image requires ~8min to pull. Current timeout insufficient for large image on existing network speed.
```

### Technique 2: Inline Critical, Reference Details

❌ **All inline** (excessive tokens):
```
Error: [full 50-line stack trace]
Configuration: [entire 200-line YAML]
Events: [all 100 events from past hour]
Logs: [full pod logs]
```

✅ **Hybrid approach** (optimal):
```
Error: [5-line excerpt of critical error]
Config: [15-line excerpt showing problem area]

Full details: Issue #123 (diagnostic phase 3)
```

### Technique 3: Use Code Blocks Efficiently

❌ **Redundant formatting**:
````
Error message:
```
Error occurred
```

Stack trace:
```
Stack trace here
```

Additional error:
```
Another error
```
````

✅ **Combined**:
````
Errors:
```
Error occurred

Stack trace here

Additional error (related)
```
````

### Technique 4: Abbreviate Repeated Information

❌ **Repetitive**:
```
Pod librechat-mongodb-abc123 in namespace ai is in status CrashLoopBackOff
Pod librechat-web-def456 in namespace ai is in status ImagePullBackOff
Pod librechat-api-ghi789 in namespace ai is in status Running
```

✅ **Concise**:
```
Pods in ai namespace:
- librechat-mongodb-*: CrashLoopBackOff
- librechat-web-*: ImagePullBackOff
- librechat-api-*: Running
```

### Technique 5: Use References for Known Patterns

❌ **Explain everything**:
```
You need to create a sealed secret. Sealed secrets are encrypted Kubernetes secrets that can be safely committed to Git repositories. They are created using the kubeseal tool with a public certificate. The sealed secret controller running in the cluster will decrypt them into regular Kubernetes secrets at runtime. This maintains GitOps principles while keeping sensitive data encrypted in the repository.
```

✅ **Reference pattern**:
```
Create SealedSecret (standard cluster pattern, cert: etc/certs/pub-sealed-secrets.pem)
```

## Complete Example Requests

### Example 1: Simple Configuration Fix

````markdown
**Bug**: #145
**Component**: flux
**Severity**: high

**Root Cause**: HelmRelease timeout (5m) insufficient for 8.2GB image pull, taking ~8min on current network.

**Error**:
```
HelmRelease/ollama.ai InstallFailed
Message: install retries exhausted
Pod: ollama-xyz ImagePullBackOff (8.2GB image)
```

**Current Config** (`apps/base/ai/ollama.yaml:15-25`):
```yaml
spec:
  interval: 12h
  timeout: 5m  # ← Too short
  chart:
    spec:
      chart: ollama
```

**Changes**:
1. File: `apps/base/ai/ollama.yaml`
   - Line ~20: `timeout: 5m` → `timeout: 15m`
   - Reason: Allow time for large image pull

**Constraints**:
- GitOps: Commit to Git, no kubectl
- Conventional commit: `fix(ai): increase ollama timeout for large image`
- Validate: `kustomize build apps/kyrion/`

**Success Criteria**:
- [ ] `flux get hr ollama -n ai` shows Ready=True
- [ ] Pod Running 1/1
- [ ] No ImagePullBackOff events

**Auto-validation (10min)**:
- HelmRelease/ollama in ai namespace
- Expected: Ready=True

**Full context**: Issue #144 (parent), diagnostic phase 3
````

**Token Count**: ~250 tokens (well under budget, clear and complete)

### Example 2: Secret Creation + Configuration

````markdown
**Bug**: #156
**Component**: kubernetes
**Severity**: high

**Root Cause**: LibreChat pods crash on startup - missing required API key environment variable (OPENAI_API_KEY) not configured in sealed secret.

**Error**:
```
Pod librechat-web-xyz CrashLoopBackOff
Container exit code: 1
Log: "Error: OPENAI_API_KEY environment variable required"
```

**Current Config** (`apps/base/ai/librechat.yaml:45-55`):
```yaml
env:
  - name: MONGODB_URI
    valueFrom:
      secretKeyRef:
        name: librechat-secret
        key: mongodb-uri
  # Missing OPENAI_API_KEY reference
```

**Changes**:
1. File: `apps/base/ai/librechat-sealed-secret.yaml`
   - Add key: `openai-api-key` with value (use kubeseal)
   - Namespace: ai (must match)

2. File: `apps/base/ai/librechat.yaml`
   - Add after line ~52:
   ```yaml
   - name: OPENAI_API_KEY
     valueFrom:
       secretKeyRef:
         name: librechat-secret
         key: openai-api-key
   ```

**Constraints**:
- Sealed Secret: Use `kubeseal --cert etc/certs/pub-sealed-secrets.pem --namespace ai`
- Value placeholder: `sk-placeholder` (user will update with real key)
- Conventional commit: `fix(ai): add OpenAI API key configuration for LibreChat`

**Success Criteria**:
- [ ] Secret decrypted: `kubectl get secret librechat-secret -n ai`
- [ ] Pod Running: `kubectl get pods -n ai -l app=librechat`
- [ ] No crash errors in logs

**Auto-validation (10min)**:
- Pods matching label app=librechat in ai namespace
- Expected: All Running 1/1

**Full context**: Issue #155 (parent), resolution plan comment 3
````

**Token Count**: ~400 tokens (efficient, includes secret creation pattern)

### Example 3: Dependency Fix

````markdown
**Bug**: #167
**Component**: flux
**Severity**: medium

**Root Cause**: Apps Kustomization deploying before infrastructure ready, causing missing CRD errors. No `dependsOn` configured.

**Error**:
```
Kustomization/apps ReconciliationFailed
Error: CustomResourceDefinition "helmreleases.helm.toolkit.fluxcd.io" not found
```

**Current Config** (`clusters/kyrion/apps.yaml:8-15`):
```yaml
kind: Kustomization
metadata:
  name: apps
spec:
  interval: 5m
  path: ./apps/kyrion
  # Missing dependsOn
```

**Changes**:
1. File: `clusters/kyrion/apps.yaml`
   - Add after line ~14:
   ```yaml
   dependsOn:
     - name: infra-configs
   ```

**Constraints**:
- GitOps workflow only
- Flux will auto-reconcile in correct order after change
- Conventional commit: `fix(flux): add dependency on infra-configs for apps kustomization`

**Success Criteria**:
- [ ] `flux get kustomizations` shows apps Ready=True
- [ ] apps waits for infra-configs to be Ready
- [ ] No CRD not found errors

**Auto-validation (10min)**:
- Kustomization/apps in flux-system namespace
- Expected: Ready=True

**Full context**: Issue #166, root cause analysis comment 2
````

**Token Count**: ~300 tokens (efficient dependency fix)

## Submitting the Request

### Using GitHub Copilot Coding Agent

After formatting the request:

1. **Update the bug issue** with the token-optimized request (use `github/github-mcp-server/create_or_update_file` or edit issue body)

2. **Assign GitHub Copilot** using the tool:
```
github/github-mcp-server/assign_copilot_to_issue(
  owner: "alecsg77",
  repo: "elysium",
  issueNumber: [bug-issue-number]
)
```

GitHub Copilot will then:
1. Read the issue with your resolution plan
2. Create a new branch
3. Implement the changes
4. Create a pull request
5. Link the PR to the issue

### Post-Submission Actions

After submitting:

1. **Update bug issue** with request status:
   ```markdown
   ## 🤖 Resolution Request Submitted
   
   Coding agent request submitted (attempt #1).
   
   Monitoring for PR creation...
   
   **Circuit Breaker**: 2 attempts remaining
   ```

2. **Monitor for PR**:
   - Check for PR creation within 15 minutes
   - If no PR, investigate or resubmit
   - If PR created, track merge status

3. **Await validation**:
   - Coordinator agent will validate after merge
   - Check Flux reconciliation status
   - Verify pods/resources healthy

## Common Request Mistakes

### Mistake 1: Too Much Context
❌ Problem: 5000-char request with full logs and configs
✅ Solution: Inline critical excerpts, reference full details

### Mistake 2: Too Little Context
❌ Problem: "Fix the timeout issue in ollama"
✅ Solution: Include error, current config, specific change needed

### Mistake 3: Ambiguous Changes
❌ Problem: "Update the configuration to fix it"
✅ Solution: "Line 20: Change `timeout: 5m` to `timeout: 15m`"

### Mistake 4: Missing Constraints
❌ Problem: No mention of sealed secrets or GitOps
✅ Solution: Explicitly state all constraints and requirements

### Mistake 5: No Validation Criteria
❌ Problem: "Make it work"
✅ Solution: Specific commands to verify success

## Token Estimation Guide

Quick estimation:
- 1 token ≈ 0.75 characters (English text)
- 1 token ≈ 1 character (code/YAML)
- Target: 1500-2000 chars = 1500-2000 tokens

Use character count as rough token estimate for this workflow.

## When to Expand Context

Add more context if:
- Complex multi-file change required
- Unusual or rare issue type
- Multiple related changes needed
- Security-sensitive modifications
- High-risk changes (e.g., database migrations)

But still stay under 3000 tokens if possible.

## Integration with Workflow

This request format ensures:
1. ✅ Coding agent has sufficient context
2. ✅ GitOps constraints are clear
3. ✅ Validation is automated
4. ✅ Circuit breaker can track attempts
5. ✅ Knowledge base can extract patterns

Optimized requests lead to better fixes and fewer failed resolution attempts.
