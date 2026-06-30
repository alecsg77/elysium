---
description: 'Guidelines for maintaining Copilot prompt files in this repository'
applyTo: '**/*.prompt.md'
---

# Prompt File Maintenance

## Scope
- Apply these rules to reusable prompt files under `.github/prompts/`.
- Treat prompts as task entry points, not as replacements for agents, runbooks, or full documentation.
- In this repository, prefer skills over prompts for most reusable operational workflows.

## Frontmatter Requirements
- Include `description` and `name`.
- Use `agent` to select `ask`, `edit`, `agent`, or a repository custom agent.
- Add `tools` only when the prompt needs to grant or narrow capabilities for execution.
- Prefer `argument-hint` for required user context such as app name, namespace, or issue number.
- Keep quoting consistent with single-quoted strings where practical.

## Prompt Design
- Start with a single clear mission.
- Organize content into predictable sections such as scope, inputs, workflow, output expectations, and quality assurance.
- Keep prompts short enough to remain discoverable and maintainable.
- Link to `/docs/` or `.github/instructions/` for detailed procedures instead of copying large templates into the prompt body.
- Ask for missing critical context once, then stop until it is available.

## When To Use a Prompt vs Agent
- Use a prompt for a narrow, reusable entry point such as deploying an app or generating a runbook.
- Use a custom agent when behavior, tools, or workflow need to be specialized across many requests.
- Do not keep prompts that are only an internal sub-step of another agent workflow unless they remain useful as a standalone user entry point.

## When To Use a Prompt vs Skill
- Prefer a skill when the workflow is multi-step, repeatable, and benefits from progressive discovery.
- Prefer a prompt only when the entry point must stay extremely thin and there is no need for a skill folder.
- If a prompt and skill would carry the same workflow, keep the skill and delete the prompt.

## Repository-Specific Rules
- Prompts for GitOps changes must reinforce base/overlay separation, version pinning, Flux validation, and sealed-secret handling.
- Prompts for docs must respect the split between `.github/` guidance and `/docs/` authoritative content.
- Prompts for diagnostics or review should prefer repository skills and the `Troubleshooter` agent when a dedicated diagnostic mode is needed.

## Quality Checks
- Remove obsolete prompts that duplicate agent internals without adding a distinct user workflow.
- Remove prompts that have been superseded by repository skills.
- Keep tool access least-privilege and update deprecated tool names.
- Verify links to runbooks, standards, and instruction files remain current.
- Re-run prompts after major edits to confirm the selected agent and expected workflow still make sense.
