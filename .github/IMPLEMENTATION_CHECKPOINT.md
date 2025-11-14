# Web-Based Troubleshooting System - Implementation Checkpoint

**Date**: 2025-01-24  
**Status**: ✅ Implementation Complete - Ready for Testing  
**Next Session**: Testing and validation

---

## Implementation Summary

Completed a comprehensive web-based troubleshooting system that enables cluster issue resolution through GitHub Issues and Copilot agents, accessible entirely from the GitHub web interface.

### What Was Built

#### 1. Issue Templates (4 files)
- `.github/ISSUE_TEMPLATE/config.yml` - Template configuration
- `.github/ISSUE_TEMPLATE/bug_report.yml` - Structured bug reports
- `.github/ISSUE_TEMPLATE/troubleshooting_request.yml` - Investigation requests
- `.github/ISSUE_TEMPLATE/feature_request.yml` - Enhancement requests

#### 2. Copilot Agents (3 files)
- `.github/agents/troubleshooter.agents.md` (~580 lines)
  - Comprehensive diagnostics (5 phases: Health Check, Resource Status, Logs, Events, Configuration)
  - Knowledge base search integration
  - Root cause analysis
  - Child bug creation workflow
  
- `.github/agents/issue-coordinator.agents.md` (613 lines)
  - Resolution plan generation
  - Approval workflow management (`/approve-plan`)
  - Token-optimized coding agent requests
  - Circuit breaker (3 attempts max)
  - Automated validation via Flux monitoring
  
- `.github/agents/knowledge-base.agents.md` (429 lines)
  - Search past issues for known fixes
  - Similarity scoring (>80% = suggest immediately)
  - Pattern extraction and documentation

#### 3. Automation (1 workflow)
- `.github/workflows/update-knowledge-base.yml` (215 lines)
  - Auto-extracts learnings from resolved issues
  - Updates KNOWN_ISSUES.md via PR
  - Triggers on issue closed with `status:resolved` label

#### 4. Guidance Documents (2 prompts)
- `.github/prompts/analyze-root-cause.prompt.md` (361 lines)
  - Systematic 7-step root cause methodology
  - Issue type classification
  - Common mistakes documentation
  
- `.github/prompts/request-resolution.prompt.md` (545 lines)
  - Token optimization guide (1500-2000 char target)
  - 9-section request structure
  - Complete examples with token counts

#### 5. User Documentation (5 files)
- `.github/TROUBLESHOOTING.md` (680 lines) - Complete user guide
- `.github/KNOWN_ISSUES.md` (285 lines) - Searchable issue database with 9 seed entries
- `.github/TROUBLESHOOTING_QUICKREF.md` - One-page quick reference
- `.github/WEB_TROUBLESHOOTING_IMPLEMENTATION.md` - Implementation details
- `.github/copilot-instructions.md` (updated +205 lines) - Web workflow section

#### 6. Updated Instructions (3 files)
- `.github/instructions/flux.instructions.md` (+121 lines)
- `.github/instructions/kubernetes.instructions.md` (+143 lines)
- `.github/instructions/helm.instructions.md` (+50 lines)

---

## Tool Reference Fixes Applied

### Issue Encountered
Initial implementation used non-existent tool names:
- ❌ `github-pull-request_copilot-coding-agent`
- ❌ `activate_commit_and_issue_tools`
- ❌ `activate_search_and_discovery_tools`

### Resolution
Updated all files to use correct tool:
- ✅ `github/github-mcp-server/assign_copilot_to_issue`

### Files Corrected
1. `.github/agents/troubleshooter.agents.md` - Tool list and MCP servers
2. `.github/agents/issue-coordinator.agents.md` - Tool list, usage instructions
3. `.github/agents/knowledge-base.agents.md` - Tool list, removed activation section
4. `.github/prompts/request-resolution.prompt.md` - Tool list, usage instructions

### User Applied Additional Fixes
User mentioned "applied some other fixes" after the tool corrections. Current file states should be verified at start of next session.

---

## How the System Works

### Workflow Overview
```
1. User creates GitHub Issue (bug report or troubleshooting request)
2. Invokes Copilot: @workspace #file:.github/agents/troubleshooter.agents.md
3. Troubleshooter runs 5-phase diagnostics (2-5 min)
4. Knowledge base searched (if >80% match, suggest fix immediately)
5. Root cause analysis → creates child bugs (one per distinct cause)
6. Issue coordinator generates resolution plans
7. User approves: /approve-plan
8. Coordinator uses github/github-mcp-server/assign_copilot_to_issue
9. GitHub Copilot creates PRs
10. Coordinator validates (10-min window: Flux status, pod health, events)
11. Success → close issues + update KB | Failure → retry (max 3) → circuit breaker
```

### Key Features
- **Zero Local Tools**: Everything via GitHub web
- **Circuit Breaker**: Max 3 auto-attempts per bug
- **Token Optimization**: 1500-2000 char requests for coding agent
- **Knowledge Base**: Auto-updates from resolved issues
- **Validation**: Monitors Flux reconciliation automatically

### Commands
- `/approve-plan` - Approve all resolution plans
- `/reject` - Reject plans, request alternatives
- `/reset-attempts` - Reset circuit breaker after manual fix

---

## Testing Plan (Next Session)

### Pre-Test Verification
1. Check copilot runners: `kubectl get pods -n arc-runners -l app.kubernetes.io/name=copilot`
2. Verify cluster access: `kubectl auth can-i get pods --as=system:serviceaccount:arc-runners:copilot-agent-readonly -A`
3. Review current file states (user applied additional fixes)

### Test Scenarios

#### Test 1: Simple Issue (Known Pattern)
- Create troubleshooting request for known issue (e.g., HelmRelease timeout)
- Verify KB search suggests fix immediately
- Confirm high confidence match (>80%)
- Try suggested fix
- Close issue with `status:resolved`
- Verify KB Last Seen date updates

#### Test 2: New Issue (Full Diagnostics)
- Create bug report for unknown issue
- Invoke troubleshooter via Copilot Chat
- Verify 5 diagnostic phases collected:
  1. Health Check (Flux, Git, reconciliation)
  2. Resource Status (conditions, inventory)
  3. Logs (error extraction)
  4. Events (timeline)
  5. Configuration (manifests, variables)
- Check root cause analysis creates child bug
- Verify resolution plan generated
- Approve with `/approve-plan`
- Monitor coding agent PR creation
- Verify coordinator validation

#### Test 3: Circuit Breaker
- Create issue with intentionally flawed resolution
- Let attempts fail (track labels: resolution-attempt:1, 2, 3)
- Verify circuit breaker triggers after 3rd failure
- Check labels: `circuit-breaker:triggered`, `needs-manual-intervention`
- Manual fix, then `/reset-attempts`
- Verify retry succeeds

#### Test 4: Multiple Root Causes
- Create troubleshooting request for multi-component failure
- Verify multiple child bugs created
- Check consolidated review comment
- Approve all with `/approve-plan`
- Monitor parallel PR creation
- Verify sequential validation

---

## Known Information

### Repository Details
- **Owner**: alecsg77
- **Repo**: elysium
- **Branch**: main
- **Cluster**: kyrion (K3s homelab)
- **Network**: Private, not cloud-accessible
- **Runners**: Self-hosted via ARC in arc-runners namespace

### MCP Servers in Use
- `flux-operator-mcp` - Flux diagnostics
- `kubernetes` - Kubernetes API access
- `github/github-mcp-server` - GitHub Issues and Copilot assignment

### Key Namespaces
- `flux-system` - Flux controllers
- `arc-runners` - GitHub Actions runners (includes copilot-runner-set)
- `ai` - AI/ML workloads (common test subject: LibreChat, Ollama)

### Common Test Issues (from KNOWN_ISSUES.md)
1. HelmRelease timeout (Flux)
2. Variable substitution failed (Flux)
3. GitRepository not syncing (Flux)
4. Pod CrashLoopBackOff - Missing ConfigMap (Kubernetes)
5. ImagePullBackOff (Kubernetes)
6. OOMKilled (Kubernetes)
7. SealedSecret not decrypting (Security)
8. LibreChat MongoDB verification error (Application)
9. GPU allocation failure (Application)

---

## Important Files for Reference

### Entry Points
- Issue creation: https://github.com/alecsg77/elysium/issues/new/choose
- Quick ref: `.github/TROUBLESHOOTING_QUICKREF.md`
- Full guide: `.github/TROUBLESHOOTING.md`

### Agent Files
- Troubleshooter: `.github/agents/troubleshooter.agents.md`
- Coordinator: `.github/agents/issue-coordinator.agents.md`
- Knowledge Base: `.github/agents/knowledge-base.agents.md`

### Workflow Files
- KB update: `.github/workflows/update-knowledge-base.yml`

### Documentation
- Main instructions: `.github/copilot-instructions.md` (see "Web-Based Troubleshooting Workflow" section)
- Known issues: `.github/KNOWN_ISSUES.md`
- Implementation details: `.github/WEB_TROUBLESHOOTING_IMPLEMENTATION.md`

---

## Questions to Ask Next Session

1. Did the test scenarios work as expected?
2. Were there any errors during diagnostic collection?
3. Did GitHub Copilot assignment via `github/github-mcp-server/assign_copilot_to_issue` work?
4. Did validation correctly detect success/failure?
5. Was the circuit breaker behavior appropriate?
6. Were the token-optimized requests clear enough for coding agent?
7. Did knowledge base search find relevant matches?
8. Any issues with the approval workflow?

---

## Potential Issues to Watch For

### During Testing
- **Runner connectivity**: Ensure copilot-runner-set pods are healthy
- **MCP server access**: Verify all 3 MCP servers accessible
- **Tool permissions**: Check ServiceAccount RBAC for read-only access
- **GitHub API limits**: Monitor for rate limiting
- **Flux reconciliation timing**: 10-min validation window may need adjustment

### User Feedback Areas
- Is 3-attempt circuit breaker threshold appropriate?
- Are diagnostic reports too verbose (50k char limit)?
- Is token optimization (1500-2000 char) sufficient?
- Should validation window be configurable?
- Are approval commands intuitive?

---

## Next Steps After Testing

If successful:
1. Update KNOWN_ISSUES.md with any new patterns discovered
2. Refine similarity scoring weights if needed
3. Adjust circuit breaker threshold if appropriate
4. Document any edge cases encountered
5. Consider adding Prometheus metrics for MTTR tracking

If issues found:
1. Document specific failures
2. Review agent logs for errors
3. Check GitHub Copilot assignment API responses
4. Verify MCP server connectivity
5. Adjust diagnostic collection if incomplete
6. Refine resolution request format if coding agent confused

---

## Success Criteria

✅ System is considered successful if:
- User can create issue and invoke diagnostics from web
- All 5 diagnostic phases collect successfully
- Root cause analysis creates appropriate child bugs
- Resolution plans are clear and actionable
- Approval workflow is intuitive
- GitHub Copilot creates PRs correctly
- Validation detects success/failure accurately
- Circuit breaker prevents infinite loops
- Knowledge base captures learnings automatically

---

**Status**: Ready to close chat and resume tomorrow for testing phase.

**Resume Command**: "I'm ready to test the web-based troubleshooting system. Let's start with Test 1 (Simple Issue with Known Pattern)."
