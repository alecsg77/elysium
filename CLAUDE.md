# Claude Code Guide

Claude Code should use `AGENTS.md` in this repository as the portable baseline.

## Start Here
- Read `AGENTS.md` first.
- Use `/docs` as the authoritative source for procedures, standards, troubleshooting, and security guidance.
- Treat `/.github/copilot-instructions.md` as a Copilot-specific overlay, not the only source of repository rules.

## Compatibility Notes
- If Claude Code does not support Copilot custom agent frontmatter, ignore the YAML metadata and follow the markdown body.
- Treat `/.github/skills/*/SKILL.md` as reusable workflow instructions.
- Treat `/.github/agents/*.agents.md` as role/workflow references when troubleshooting or coordinating issue flows.

## Repository Priorities
- Preserve Copilot compatibility whenever editing shared customization files.
- Keep GitOps rules, secret handling, validation commands, and documentation placement aligned with `AGENTS.md` and `/docs`.
- Do not weaken or remove Copilot-specific workflows unless a portable replacement exists.
