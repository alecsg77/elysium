# Web-Based Troubleshooting Workflow

Guide for diagnosing and resolving Kubernetes cluster issues using GitHub Issues and Copilot Chat from any web browser.

## Quick Start (5 Steps)

```
1. Create Issue → 2. Invoke Copilot → 3. Review Analysis → 4. Approve Plan → 5. Auto-Resolve
```

### 1. Create Issue

Go to: https://github.com/alecsg77/elysium/issues/new/choose

**Select template:**
- **🔍 Troubleshooting Request** - Need investigation (unclear issue)
- **🐛 Bug Report** - Known issue with symptoms

**Provide:**
- Component (Flux/Kubernetes/Application/Network)
- Namespace and resource name
- Error messages (exact text)
- Recent changes
- Affected services

### 2. Invoke Copilot

In GitHub Copilot Chat on issue page:

```
#file:.github/agents/troubleshooter.agents.md
Please investigate this issue and run diagnostics
```

**Wait 2-5 minutes** for diagnostic collection.

### 3. Review Analysis

Copilot posts **5 diagnostic phases**:
1. **Health Check** - System status (Flux, Git sync)
2. **Resource Status** - Kubernetes/Flux conditions
3. **Logs** - Error extraction
4. **Events** - Chronological timeline
5. **Configuration** - Manifests and variables

Then **creates child bugs** (one per root cause) with detailed analysis and resolution plans.

### 4. Approve Plan

Review consolidated comment with all resolution plans.

**Approve all:**
```
/approve-plan
```

**Request changes:**
```
/reject
[Explain what needs adjustment]
```

### 5. Auto-Resolve

- ✅ Coding agent creates PRs
- ✅ Changes deployed via Flux (10-min validation window)
- ✅ Issues auto-close on success
- ✅ Knowledge base auto-updates

If failure → retry (max 3 attempts) → circuit breaker → manual intervention

---

## Commands

| Command | Purpose |
|---------|---------|
| `/approve-plan` | Approve all resolution plans in review |
| `/reject` | Reject plans, request alternative approach |
| `/reset-attempts` | Reset circuit breaker after manual intervention |

---

## Data Handling & Security

**Before submitting an issue, redact sensitive information:**

- ❌ Never paste: API keys, kubeconfigs, tokens, OAuth secrets, bearer tokens
- ✏️ Replace with: `[REDACTED_TOKEN]`, `<DATABASE_HOST>`, etc.
- 📝 Acknowledge redactions: `Token value redacted; reference event at 2025-12-13T10:00Z`

**Quick secret scan:**
```bash
rg -n 'password|secret|token|apikey|bearer|BEGIN.*PRIVATE' diagnostics/ logs/
grep -Ri 'secret\|password\|token' diagnostics/ logs/
```

Redact matches before sharing.

---

## Detailed Workflow

### Issue Templates

#### Troubleshooting Request
Use when: "Something's wrong, but I don't know exactly what"

Provide:
- Component affected
- Impact level
- Symptoms observed
- Affected services
- When it started
- Recent changes
- Error messages (if any)

#### Bug Report
Use when: "I know what's broken"

Provide:
- Component
- Severity (Critical/High/Medium/Low)
- Namespace and resource
- Exact error messages
- Steps to reproduce
- Expected vs actual behavior

### Diagnostic Phases

#### Phase 1: Health Check
- Flux controller pods running
- GitRepository sync status
- Kustomization/HelmRelease ready status

#### Phase 2: Resource Status
- Detailed condition messages
- Inventory of managed resources
- Dependency status

#### Phase 3: Logs
- Controller logs (filtered for errors)
- Application pod logs
- Error pattern extraction

#### Phase 4: Events
- Chronological event timeline
- Warning and error events
- Timestamps for correlation

#### Phase 5: Configuration
- Deployed manifests
- Variable substitution status
- Reference configurations

### Root Cause Analysis

Copilot identifies **distinct root causes** and creates one child bug per cause:

- **Independent causes**: Each gets separate bug
- **Cascading failures**: Grouped as single root cause
- **Symptoms vs causes**: Separated clearly

Each child bug includes:
- Detailed description
- Root cause explanation
- Proposed resolution
- Acceptance criteria

### Approval Process

**Review consolidated comment** listing all child bugs and resolution plans.

**For each plan, verify:**
- ✓ Root cause is accurate
- ✓ Proposed fix addresses it
- ✓ No unintended side effects
- ✓ Validation steps are clear

**Approve all at once:**
```
/approve-plan
```

---

## Circuit Breaker System

Auto-stops retries after 3 failed attempts to prevent infinite loops.

| Attempt | Status | Action |
|---------|--------|--------|
| 1 | First try | Submit to coding agent |
| 2 | Retry | Adjust plan based on failure |
| 3 | Final attempt | Last automated try |
| 3+ | **Triggered** | Manual intervention required |

**To reset after manual fix:**
```
/reset-attempts
Manually fixed [issue]. Ready to retry.
```

---

## Tips and Best Practices

### Reporting Issues

✅ **Do:**
- Include exact error messages
- Note when problem started
- List recent changes
- Provide namespace and resource names
- Use appropriate severity level

❌ **Don't:**
- Paste secrets or credentials
- Submit vague descriptions ("it's broken")
- Report multiple unrelated issues in one ticket
- Dump entire log files (summarize + link)

### During Investigation

✅ **Do:**
- Review diagnostic reports carefully
- Check if similar issues exist
- Be patient (diagnostics take 2-5 minutes)

❌ **Don't:**
- Make manual changes while Copilot investigates
- Submit duplicate requests
- Interrupt in progress investigations

### Approving Plans

✅ **Do:**
- Read resolution plans completely
- Verify changes match root cause
- Consider impact and timing
- Ask questions if unsure

❌ **Don't:**
- Auto-approve without review
- Approve changes you don't understand
- Proceed if you have concerns

---

## Common Issues

See [Known Issues and Troubleshooting](known-issues.md) for:
- HelmRelease timeouts
- Variable substitution failures
- Pod crashes
- Storage issues
- Application-specific problems

---

## Example Workflow

```
User creates issue: "LibreChat pods restarting every 2 minutes"
↓
Invokes troubleshooter agent via Copilot Chat
↓
Copilot runs diagnostics (2-5 min):
  - Health Check: Flux OK, Git synced
  - Resources: LibreChat HelmRelease Ready, pods CrashLoopBackOff
  - Logs: MongoDB connection failed
  - Events: Restarts every 2min, MongoDB pod failing
  - Config: Memory requests too high vs node capacity
↓
Creates child bug: "Root Cause: Insufficient memory for MongoDB"
↓
User reviews and approves: `/approve-plan`
↓
Coding agent creates PR: Reduce Coder memory request from 4Gi to 512Mi
↓
Flux reconciles changes (5-10 min)
↓
Coordinator validates: MongoDB pod now Running, LibreChat healthy
↓
Issues auto-closed, knowledge base updated
```

---

## When to Seek Help

Create a new troubleshooting issue if:
- Suggested fix doesn't resolve the problem
- Issue doesn't match known patterns
- You need clarification on diagnostics
- Automated resolution failed after 3 retries

Include:
- Original issue number
- What you tried
- Results (success/failure details)
- New error messages
