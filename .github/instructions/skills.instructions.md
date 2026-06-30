---
description: 'Guidelines for maintaining Copilot skill files in this repository'
applyTo: '**/SKILL.md'
---

# Skill File Maintenance

## Scope
- Apply these rules to repository skills under `.github/skills/<name>/SKILL.md`.
- Use skills for on-demand, repeatable workflows that benefit from focused instructions and optional bundled assets.

## Frontmatter Requirements
- Include `name` and `description`.
- Keep `name` identical to the containing folder name.
- Write `description` as the discovery surface with concrete trigger phrases and “Use when...” wording.

## Repository Preference
- Prefer skills over prompt files for user-invocable workflows in this repository.
- Keep agents for orchestration, role separation, handoffs, or explicit tool boundaries.
- Keep instructions for always-on or file-scoped rules.
- Write skill bodies so they remain useful as plain markdown workflow documents for Claude Code and other hosts that do not natively load Copilot skills.

## Content Rules
- Start with when to use and when not to use the skill.
- Keep workflows focused and scannable.
- Reference `/docs/` and `.github/instructions/` rather than duplicating long procedures.
- Bundle assets only when they materially improve execution.
- Avoid relying on skill-only runtime features inside the body; the markdown should still make sense if an agent simply reads the file.

## Quality Checks
- Verify the skill has a distinct purpose from neighboring skills and agents.
- Avoid copying whole runbooks into `SKILL.md`.
- Re-test discovery after changing the description or folder name.