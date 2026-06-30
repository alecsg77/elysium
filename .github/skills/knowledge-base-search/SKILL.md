---
name: 'knowledge-base-search'
description: 'Search historical GitHub issues and local troubleshooting docs for reusable fixes. Use when asked whether an incident happened before, when looking for similar failures, or when ranking likely known fixes before deeper diagnostics.'
---

# Knowledge Base Search

## When To Use
- Use this skill before or during troubleshooting when pattern reuse might save time.
- Use it when the user asks whether a failure has happened before.
- Use it to search closed GitHub issues and `/docs/troubleshooting/known-issues.md` together.

## Workflow
1. Extract component, error phrases, resource type, resource name, and symptoms.
2. Search closed issues with the tightest useful query first.
3. Search `docs/troubleshooting/known-issues.md` for local patterns.
4. Rank matches by error similarity, component, resource type, root cause, and symptom overlap.
5. Return high-confidence known fixes first; otherwise provide contextual references only.

## Output Rules
- State confidence clearly.
- Separate exact or near-exact matches from weak analogies.
- Avoid claiming a known fix when the evidence is thin.

## References
- `/docs/troubleshooting/known-issues.md`
- `/docs/troubleshooting/web-troubleshooting.md`
- `.github/agents/troubleshooter.agents.md`