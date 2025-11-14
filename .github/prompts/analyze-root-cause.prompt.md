---
agent: 'agent'
model: Claude Sonnet 4.5
tools: ['runCommands', 'search', 'flux-operator-mcp/get_flux_instance', 'flux-operator-mcp/get_kubernetes_resources', 'kubernetes/resources_get', 'kubernetes/resources_list', 'kubernetes/events_list', 'fetch', 'githubRepo']
description: 'Systematically analyze diagnostic data to identify distinct root causes'
---

# Root Cause Analysis

You are performing root cause analysis on cluster issues based on diagnostic data collected by the troubleshooter agent.

## Objective

Identify **distinct, independent root causes** from diagnostic data, separating them from:
- **Symptoms** (observable effects like pod crashes)
- **Cascading failures** (failures caused by upstream issues)
- **Related but independent issues** (multiple separate problems)

## Analysis Methodology

### Step 1: Review Diagnostic Data

Read all diagnostic phase comments from the troubleshooting issue:

1. **Health Check Summary**
   - Note which components are healthy vs failing
   - Identify controller status
   - List failed Kustomizations/HelmReleases

2. **Resource Status Analysis**
   - Examine resource conditions and status
   - Note reconciliation states
   - Identify stuck or pending resources

3. **Logs Analysis**
   - Extract error messages
   - Note error patterns and frequencies
   - Identify stack traces and root exceptions

4. **Events Timeline**
   - Order events chronologically
   - Identify first failure point
   - Track propagation of failures

5. **Configuration Review**
   - Review resource configurations
   - Check for misconfigurations
   - Verify dependencies and references

### Step 2: Identify Failure Chain

Map the sequence of failures to distinguish cause from effect:

```
Primary Failure (Root Cause)
    ↓
Secondary Failure (Symptom)
    ↓
Tertiary Failure (Cascading Effect)
```

**Example**:
```
ConfigMap missing (ROOT CAUSE)
    ↓
Pod fails to start with config error (SYMPTOM)
    ↓
Service has no endpoints (CASCADING)
    ↓
Ingress returns 503 (CASCADING)
```

**Action**: Create **ONE** bug issue for the ConfigMap missing, not separate issues for each symptom.

### Step 3: Apply Root Cause Criteria

A **valid root cause** must meet ALL criteria:

| Criterion | Description | Example Pass | Example Fail |
|-----------|-------------|--------------|--------------|
| **Independent** | Can occur without other failures | Network policy blocking traffic | Pod crash (depends on why) |
| **Actionable** | Can be fixed with specific changes | Invalid Helm values | "System unstable" |
| **Verifiable** | Can confirm it's the cause | Error logs point to missing secret | Vague symptoms |
| **Isolated** | Fixing it doesn't require fixing others | Timeout value too low | Multiple config errors |

### Step 4: Distinguish Issue Types

#### Type A: Configuration Issues
**Indicators**:
- Resources referencing non-existent ConfigMaps/Secrets
- Invalid YAML structure or values
- Missing required fields
- Incorrect resource names/namespaces

**Root Cause**: The configuration error itself

**Example**: HelmRelease references `valuesFrom: secret-name` but secret doesn't exist
- Root Cause: Missing Secret
- Fix: Create the Secret (or SealedSecret)

#### Type B: Dependency Issues
**Indicators**:
- Kustomization waiting on dependency
- CRDs not installed before resources
- Services starting before databases ready

**Root Cause**: Dependency order violation

**Example**: Application Kustomization deployed before infrastructure controllers
- Root Cause: Missing `dependsOn` in Kustomization
- Fix: Add dependency declaration

#### Type C: Resource Constraints
**Indicators**:
- OOMKilled pods
- Pending pods with "insufficient resources"
- Slow reconciliation

**Root Cause**: Resource limits or node capacity

**Example**: Pod requests 32Gi memory but nodes only have 16Gi
- Root Cause: Unrealistic resource requests
- Fix: Adjust resource requests to match cluster capacity

#### Type D: Timing/Timeout Issues
**Indicators**:
- "timeout exceeded" errors
- "context deadline exceeded"
- Reconciliation failures after N minutes

**Root Cause**: Timeout too short for operation

**Example**: HelmRelease timeout=5m but chart takes 8m to deploy
- Root Cause: Insufficient timeout
- Fix: Increase timeout value

#### Type E: External Dependencies
**Indicators**:
- Image pull errors
- External mount failures
- Network connectivity issues

**Root Cause**: External resource unavailable

**Example**: Init container waiting for `/mnt/storage` mount that never appears
- Root Cause: External storage not mounted
- Fix: Fix mount configuration or add mount detection

#### Type F: Cascading Failures
**Indicators**:
- Multiple failures with same timestamp
- Errors mentioning upstream failures
- "Dependency not ready" messages

**Root Cause**: ONE upstream failure causing many effects

**Example**: Sealed-secrets controller crashed, causing 10 pods to fail secret decryption
- Root Cause: Sealed-secrets controller crash (ONE issue)
- NOT: 10 separate secret decryption failures

### Step 5: Group Related Symptoms

When multiple failures share a root cause:

**Merge these into ONE bug issue**:
- Same component failing multiple times
- Multiple resources affected by same config error  
- Cascading failures from one source
- Symptoms of single underlying problem

**Example Grouping**:

**Diagnostic Findings**:
1. Pod A CrashLoopBackOff
2. Pod B CrashLoopBackOff
3. Pod C ImagePullBackOff
4. Service has no endpoints
5. HelmRelease install failed

**Root Cause Analysis**:
- Pods A & B: Both crash with "missing /config/app.yaml"
- Pod C: Different issue - image doesn't exist
- Service & HelmRelease: Cascading from pod failures

**Result**: **TWO** bug issues:
1. Issue #1: Missing ConfigMap causing Pods A & B to crash (includes service/HelmRelease symptoms)
2. Issue #2: Invalid image reference for Pod C

### Step 6: Write Root Cause Summary

For each identified root cause, document:

```markdown
#### Root Cause #N: [Brief Title - 5-7 words]

**Type**: [Configuration/Dependency/Resource/Timing/External/Cascading]

**Component**: [Flux CD/Kubernetes/Helm/Networking/Application]

**Symptoms Observed**:
- [Symptom 1] (see diagnostic phase X)
- [Symptom 2] (see diagnostic phase X)
- [Symptom 3] (see diagnostic phase X)

**Underlying Issue**:
[2-3 sentences explaining the technical root cause]

**Evidence**:
- Error message: `[exact error from logs]`
- Failed resource: [resource type/name/namespace]
- Configuration issue: [specific config problem]
- Timeline: First appeared at [timestamp]

**Impact**:
- **Severity**: Critical/High/Medium/Low
- **Scope**: [namespace/cluster-wide/single resource]
- **Services Affected**: [list]

**Dependencies**:
- Independent / Depends on Root Cause #X being fixed first

**Confidence**: High/Medium/Low (how certain we are this is the root cause)
```

### Step 7: Validate Completeness

Before finalizing root cause analysis:

✅ **Checklist**:
- [ ] All observed symptoms are explained by identified root causes
- [ ] No duplicate causes (similar issues merged)
- [ ] Each cause is independent and actionable
- [ ] Cascading failures are attributed to primary cause
- [ ] Evidence clearly links cause to symptoms
- [ ] Dependencies between causes are noted
- [ ] Confidence levels are honest (note uncertainties)

## Common Analysis Mistakes

### Mistake 1: Confusing Symptom with Cause

❌ **Wrong**: "Root cause is pod CrashLoopBackOff"
✅ **Right**: "Root cause is missing environment variable causing application to crash on startup, resulting in CrashLoopBackOff"

### Mistake 2: Creating Issues for Cascading Failures

❌ **Wrong**: 
- Issue #1: Service has no endpoints
- Issue #2: Ingress returns 503
- Issue #3: Pod not running

✅ **Right**:
- Issue #1: Pod not running due to [root cause] (includes service/ingress symptoms)

### Mistake 3: Over-Grouping Unrelated Issues

❌ **Wrong**: "All pods in namespace failing" → One issue
✅ **Right**: Separate issues if pods fail for different reasons (missing secret, wrong image, resource limits)

### Mistake 4: Under-Grouping Related Issues

❌ **Wrong**:
- Issue #1: MongoDB pod crashing
- Issue #2: LibreChat pod can't connect to MongoDB
- Issue #3: LibreChat HelmRelease install failed

✅ **Right**: One issue for MongoDB failure (other symptoms are effects)

### Mistake 5: Vague Root Causes

❌ **Wrong**: "System is broken" or "Flux not working"
✅ **Right**: "HelmRelease timeout value (5m) insufficient for large container image (8GB)"

## Output Format

Post root cause analysis as comment on troubleshooting issue:

```markdown
## 🎯 Root Cause Analysis

Diagnostic data has been analyzed. Identified **[N] distinct root causes**:

---

### Root Cause #1: [Title]
[Full root cause documentation from template above]

---

### Root Cause #2: [Title]
[Full root cause documentation from template above]

---

### Root Cause #3: [Title]
[Full root cause documentation from template above]

---

## Summary

**Total Root Causes**: [N]
**Independent Issues**: [N] (can be fixed in parallel)
**Dependent Issues**: [N] (require sequential fixes)

**Recommended Fix Order**:
1. Root Cause #[X] - [Dependency required for others]
2. Root Cause #[Y] - [Can be done after #X]
3. Root Cause #[Z] - [Independent, can be done anytime]

---

**Next Steps**:
1. Creating child bug issues for each root cause
2. Linking child issues to this investigation
3. Generating resolution plans
4. Awaiting approval to proceed with fixes

---

**Confidence Level**: High / Medium / Low

[If confidence is not High, explain what additional information would help confirm root causes]
```

## When Uncertain

If root cause is unclear after analysis:

```markdown
## ⚠️ Root Cause Analysis - Further Investigation Needed

**Symptoms Identified**: [List]

**Possible Root Causes**:
1. [Hypothesis 1] - Evidence: [what supports this]
2. [Hypothesis 2] - Evidence: [what supports this]

**To Confirm**, need to:
- [ ] Check [specific resource/log]
- [ ] Test [specific hypothesis]
- [ ] Gather [additional data]

Proceeding with additional diagnostics before creating bug issues.
```

It's better to **gather more data** than create bug issues for wrong root causes.

## Integration with Workflow

This analysis feeds into:

1. **Bug Issue Creation**: Each root cause → one bug issue
2. **Resolution Planning**: Issue coordinator generates plans per root cause
3. **Knowledge Base**: Patterns identified help future troubleshooting
4. **Documentation**: Common causes added to runbooks

Accurate root cause analysis is **critical** for efficient resolution and prevents wasted effort on fixing symptoms instead of causes.
