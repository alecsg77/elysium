---
description: 'Guidelines for maintaining repository-specific Copilot instruction files'
applyTo: '**/*.instructions.md'
---

# Instruction File Maintenance

## Scope
- Apply these rules when editing repository-level instruction files under `.github/instructions/`.
- Keep instructions concise, targeted, and directly useful to Copilot in this repository.

## Frontmatter Requirements
- Include `description` and `applyTo` in every instruction file.
- Use narrow `applyTo` globs whenever possible.
- Avoid `applyTo: '**'` unless the instruction truly applies across the entire repository.

## Content Rules
- Focus on conventions, constraints, and decision rules.
- Reference `/docs/` for step-by-step procedures and long-form explanations.
- Avoid repeating the same guidance across multiple instruction files unless the repetition is intentional and low-cost.
- Prefer repository-specific examples and paths over generic prose.

## Repository-Specific Rules
- Keep `.github/` files machine-first: patterns, standards, triggers, and quick references.
- Keep `/docs/` authoritative: runbooks, architecture, troubleshooting, and operational detail.
- For YAML-focused instructions, emphasize GitOps ordering, base/overlay separation, and sealed-secret requirements.
- For customization-maintenance instructions, emphasize discovery metadata, least-privilege tools, and removal of obsolete prompt or agent surfaces.

## Quality Checks
- Revisit `applyTo` globs when repository structure changes.
- Remove stale references to deprecated tools, old workflows, or superseded prompts and agents.
- Ensure each instruction has a clearly distinct purpose from neighboring files.
- Validate that the instruction helps Copilot choose the correct behavior without duplicating a runbook.
