---
description: 'Guidelines for maintaining custom Copilot agent files in this repository'
applyTo: '**/*.agents.md,**/*.agent.md'
---

# Custom Agent Maintenance

## Scope
- Apply these rules when creating or updating repository-level custom agents under `.github/agents/`.
- Optimize for clear discovery, least-privilege tool access, and workflows that match this GitOps repository.

## Frontmatter Requirements
- Include `description` and make it the primary discovery surface.
- Add `name` for stable display in the UI.
- Prefer explicit `tools` instead of implicit full access.
- Declare `model` when the agent depends on a specific reasoning tier.
- Use `target` only when the agent is intentionally environment-specific.
- Use `handoffs` only for real workflow transitions, not as a generic navigation list.
- Keep Copilot-specific frontmatter valid, but ensure the markdown body still reads well as plain instructions for hosts that ignore metadata.

## Tool Selection
- Prefer current stable aliases and namespaces such as `read`, `edit`, `search`, `execute`, `agent`, `todo`, `web/fetch`, and `github/*`.
- Keep tool lists minimal. Add cluster, Grafana, Flux, or other MCP namespaces only when the agent must use them directly.
- Remove legacy or ambiguous tool identifiers when a stable alias exists.
- If an orchestrator agent invokes subagents, include every tool family those subagents require.

## Prompt Structure
- State the agent role and authority boundaries near the top of the file.
- Define the workflow in ordered phases when the agent performs multi-step work.
- Prefer short, explicit instructions over long reusable prose blocks.
- Reference authoritative repository docs under `/docs/` instead of duplicating full procedures.
- Separate root causes from symptoms and decisions from examples.

## Repository-Specific Rules
- Keep GitOps agents repository-aware: respect base/overlay separation, Flux dependency ordering, and sealed-secret requirements.
- Prefer skills for user-facing, repeatable workflows that do not require subagent isolation or dedicated tool boundaries.
- Avoid embedding full runbooks in agents. Summarize the workflow and link to `/docs/runbooks/`.
- Do not add implementation authority to agents whose role is review, planning, diagnostics, or coordination only.
- Use handoffs for natural flows such as diagnostics → coordination or review → planning.
- In this repository, keep agents mainly for orchestration, coordination, troubleshooting mode, and other explicit role-based boundaries.
- Prefer built-in `Plan` plus repository skills over custom planning or review agents unless a distinct role boundary is required.
- `Issue Coordinator` is an intentional exception: keep it as an agent because it is the coordination boundary for GitHub issue workflow, coding-agent handoff, and post-diagnostic approval flow.
- When an agent exists mainly as an internal handoff target, prefer `user-invocable: false` to keep the picker focused.
- Mirror critical repository-wide rules in `/AGENTS.md` so non-Copilot agents are not forced to parse `.github` customizations to behave correctly.

## Quality Checks
- Verify the filename and `name` reflect the agent purpose.
- Check that descriptions include concrete trigger phrases a user would actually type.
- Remove duplicate agents or prompt content that only restates another agent or skill without adding a distinct entry point.
- Re-test any agent after changing tools, names, or handoffs.
