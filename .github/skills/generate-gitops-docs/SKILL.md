---
name: 'generate-gitops-docs'
description: 'Generate or update GitOps documentation for this repository. Use when asked to write application READMEs, runbooks, architecture notes, troubleshooting guides, or other docs tied to apps, infrastructure, monitoring, or cluster operations.'
---

# Generate GitOps Docs

## When To Use
- Use this skill when the user wants documentation created or updated for this repository.
- Use it for app READMEs, runbooks, architecture docs, troubleshooting content, and standards-adjacent documentation.
- Do not use it to invent workflows that contradict existing `/docs/` guidance.

## Inputs
- Documentation type.
- Target path or target component.
- Whether this is new documentation or an update to existing docs.

## Workflow
1. Determine whether the content belongs under `/docs/` or beside the source directory.
2. Reuse existing repository structure and topic README patterns.
3. Reference manifests, values files, and runbooks instead of duplicating large YAML blocks.
4. Keep `.github/` content machine-first and `/docs/` content authoritative and human-first.
5. Update cross-links when the new document changes navigation.

## Repository Rules
- Runbooks live in `/docs/runbooks/`.
- General architecture, standards, security, and troubleshooting docs live under `/docs/`.
- Code-adjacent docs such as app READMEs live alongside the relevant source.
- `.github/` should contain guidance, not full operational runbooks.

## Quality Gates
- Confirm placement matches `/docs/standards/repository-structure.md`.
- Ensure links target existing repository paths.
- Avoid duplicating procedures already documented elsewhere.

## References
- `.github/instructions/documentation.instructions.md`
- `/docs/README.md`
- `/docs/standards/repository-structure.md`