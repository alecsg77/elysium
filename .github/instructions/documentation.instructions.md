---
applyTo: "**/*.md,**/*.yaml,**/*.yml"
description: "Documentation standards for GitOps repository"
---

# Documentation Standards

## Documentation Hierarchy and Roles

This repository maintains a **strict separation** between AI agent guidance and human/AI documentation:

### `.github/` Folder - AI Agent Context (Machine-First)
**Purpose**: Provide context and guidance for GitHub Copilot and automated agents

| Directory | Content Type | Purpose | Audience |
|-----------|-------------|---------|----------|
| `.github/instructions/*.instructions.md` | **Agent instructions** | Coding standards, patterns, conventions with references to actual docs | GitHub Copilot (coding) |
| `.github/agents/*.agents.md` | **Agent definitions** | Agent behavior, workflows, coordination logic | GitHub Copilot (agents) |
| `.github/prompts/*.prompt.md` | **Copilot prompts** | Task-specific agent guidance with quick references | GitHub Copilot (prompts) |

**Rules for `.github/` content**:
- ✅ Provide patterns, conventions, and best practices
- ✅ Include quick reference templates and examples
- ✅ Link to detailed documentation in `/docs/`
- ✅ Focus on "how to code" and "what patterns to follow"
- ❌ **NO step-by-step procedures** (those go in `/docs/runbooks/`)
- ❌ **NO comprehensive documentation** (that goes in `/docs/standards/`)
- ❌ **NO duplicating information** from `/docs/`

**Example content**:
- `kubernetes.instructions.md`: Manifest patterns, security standards, resource conventions
- `flux.instructions.md`: GitOps patterns, dependency chains, reconciliation strategies
- `deploy-app.prompt.md`: High-level workflow, key principles, links to detailed runbook

### `/docs/` Folder - Authoritative Documentation (Human-First)
**Purpose**: Single source of truth for standards, procedures, architecture, and troubleshooting

| Directory | Content Type | Purpose | Audience |
|-----------|-------------|---------|----------|
| `/docs/standards/` | **Standards & rules** | Repository structure, naming, best practices, anti-patterns | Humans & AI |
| `/docs/runbooks/` | **Procedures** | Step-by-step operational guides with commands and validation | Humans & AI |
| `/docs/architecture/` | **Architecture docs** | System design, topology, network, storage | Humans |
| `/docs/security/` | **Security docs** | Policies, secret management, RBAC, incident response | Humans |
| `/docs/troubleshooting/` | **Troubleshooting** | Known issues, diagnostic workflows, resolutions | Humans & AI |

**Rules for `/docs/` content**:
- ✅ Comprehensive, authoritative information
- ✅ Step-by-step procedures with validation steps
- ✅ Complete examples with context
- ✅ Clear prerequisites and expected outcomes
- ✅ Reference external official documentation
- ❌ **NO agent-specific instructions** (those go in `.github/instructions/`)
- ❌ **NO duplication** between standards and runbooks

**Example content**:
- `standards/repository-structure.md`: Decision tree, hygiene rules, naming conventions, anti-patterns
- `runbooks/add-application.md`: Complete 8-step procedure with commands, validation, troubleshooting
- `troubleshooting/known-issues.md`: Searchable knowledge base with symptoms, causes, resolutions

### Cross-Reference Pattern

**From `.github/` → Reference `/docs/`**:
```markdown
<!-- In .github/instructions/kubernetes.instructions.md -->
For complete deployment procedures, see:
- [Add Application Runbook](/docs/runbooks/add-application.md)
- [Repository Structure Standards](/docs/standards/repository-structure.md)
```

**From `/docs/` → Reference other `/docs/`**:
```markdown
<!-- In docs/runbooks/add-application.md -->
For file placement rules, see [Repository Structure Standards](/docs/standards/repository-structure.md)
```

**Never**: `/docs/` should NOT reference `.github/` files (those are agent-internal)

## General Guidelines
- Centralize all documentation under `/docs` only; do not place docs in app or infrastructure directories
- Use clear, concise language accessible to team members
- Update documentation alongside code changes
- Include practical examples for complex patterns (reference source files rather than duplicating YAML)
- Link to official documentation for third-party tools
- Use relative links targeting `/docs/...` paths across the repository

## `/docs` Scope and Indexing
Only general project documentation is stored under `/docs` (architecture, runbooks, security, standards, troubleshooting). Code-adjacent documentation (apps, infrastructure, monitoring, coder templates, functions, scripts) MUST live alongside their source folders.

### Required Layout
- `/docs/README.md`: Root index with overview and navigation to topic indexes
- `/docs/architecture/README.md`: Cluster topology, network, storage, security boundaries
- `/docs/security/README.md`: Secret management, RBAC, policies, incident response
- `/docs/runbooks/`: Operational procedures and playbooks (one file per task)
- `/docs/troubleshooting/`: Common errors, diagnostic workflows, fixes
- `/docs/standards/`: Coding, documentation, and repository standards
- `/docs/assets/`: Shared images and diagrams (topic-specific assets may also be co-located)

### Topic README Content
Each topic folder MUST include a `README.md` that describes:
- **Overview**: Purpose and scope of the topic
- **Contents**: Indexed list of files and subtopics
- **Usage/Procedures**: How to use or execute relevant tasks
- **Dependencies**: Prerequisites and required components
- **Configuration**: Key options and variables, with links to source files
- **Examples**: Minimal examples referencing source manifests
- **Troubleshooting**: Known issues and solutions

## Inline Documentation
- Add YAML comments for non-obvious configuration choices
- Document why specific values or patterns are used
- Explain dependency relationships and ordering
- Note any workarounds or temporary solutions
- Reference relevant issues or documentation links

## Application Documentation
For each application, create documentation in the app’s source directory (e.g., `apps/base/<app>/README.md`):
- Document application purpose and functionality
- List exposed services and ingress endpoints
- Describe configuration options and customization
- Include upgrade and rollback procedures
- Note resource requirements and scaling considerations
- Document backup and restore procedures
- Link to manifests and values in `apps/` using relative paths; avoid duplicating full YAML in docs

## Architecture Documentation
Maintain high-level architecture documentation in `/docs/architecture/`:
- Cluster topology and node roles
- Network architecture and service mesh
- Storage architecture and PVC management
- Security boundaries and access controls
- Monitoring and observability stack
- Disaster recovery procedures

## Change Documentation

### Conventional Commits Specification
All commit messages MUST follow the [Conventional Commits specification](https://www.conventionalcommits.org/en/v1.0.0/).

**Format**:
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types**:
- `feat`: New feature or capability
- `fix`: Bug fix or correction
- `docs`: Documentation changes only
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `build`: Changes to build system or dependencies
- `ci`: Changes to CI/CD configuration
- `chore`: Other changes that don't modify src or test files
- `revert`: Reverts a previous commit

**Scopes** (for this repository):
- `flux`: Flux CD configuration changes
- `apps`: Application deployments
- `infra`: Infrastructure components
- `monitoring`: Monitoring stack changes
- `secrets`: Secret management changes
- `helm`: Helm chart configurations
- `kustomize`: Kustomize overlays
- `ci`: CI/CD workflows
- `docs`: Documentation updates
- `cluster`: Cluster-wide configuration

**Breaking Changes**:
- Add `!` after type/scope: `feat(apps)!: migrate to new chart version`
- Include `BREAKING CHANGE:` in footer with description

**Examples**:
```
feat(apps): add librechat AI chat application

Add LibreChat with MongoDB backend for multi-model LLM conversations.
Includes sealed secrets for API keys and Tailscale ingress.

Closes #123

---

fix(monitoring): resolve Prometheus scrape timeout

Increase scrape interval from 30s to 60s to prevent timeout errors
on high-cardinality endpoints.

---

docs(flux): add troubleshooting runbook for failed HelmReleases

---

feat(infra)!: upgrade cert-manager to v1.15

BREAKING CHANGE: cert-manager v1.15 removes support for deprecated
v1alpha2 API. All Certificate resources must be migrated to v1.
Migration guide: docs/cert-manager-migration.md
```

**General Guidelines**:
- Use imperative mood in description ("add" not "added")
- Keep description under 72 characters
- Capitalize first letter of description
- No period at end of description
- Use body to explain what and why, not how
- Reference issues/PRs in footer
- Document breaking changes prominently
- Include migration guides for major changes
- Tag releases with comprehensive changelogs

## Runbook Documentation

**Location**: `/docs/runbooks/` (NOT `.github/prompts/`)

Runbooks are **step-by-step operational procedures** for humans and AI agents to follow.

**Runbook structure** (required sections):
1. **Prerequisites**: Tools, access, knowledge required
2. **Overview**: Brief description and estimated time
3. **Step-by-step procedure**: Numbered steps with exact commands
4. **Validation**: How to verify success after each major step
5. **Troubleshooting**: Common issues and their solutions
6. **Related Documentation**: Links to relevant standards and guides
7. **Checklist**: Pre-action and post-action verification items

**Common runbook topics**:
- Cluster bootstrap and initialization
- Adding new applications or services
- Secret rotation procedures
- Scaling applications up or down
- Troubleshooting common issues
- Disaster recovery procedures
- Upgrading cluster components
- Backup and restore operations

**Runbook vs Prompt distinction**:
- **Runbook** (`/docs/runbooks/add-application.md`): Complete procedure with all commands, validation steps, troubleshooting - authoritative source
- **Prompt** (`.github/prompts/deploy-app.prompt.md`): Agent guidance that **references** the runbook, provides high-level workflow and key principles

## Diagram Standards
- Use mermaid diagrams for architecture visualization
- Embed diagrams in markdown files
- Keep diagrams simple and focused
- Update diagrams when architecture changes
- Include dependency flow diagrams
- Document network topology visually
- Store shared diagrams under `/docs/assets/` or co-locate within the relevant topic folder

## API and Interface Documentation
- Document custom CRDs with examples (reference source files rather than duplicating YAML)
- Explain Flux variable substitution patterns
- List available ConfigMap and Secret references
- Document service endpoints and APIs
- Describe ingress patterns and routing rules

## Security Documentation
- Document secret management procedures
- List security boundaries and controls
- Explain RBAC roles and permissions
- Document network policies
- Describe certificate management
- Include security incident response procedures
- Place all security documentation under `/docs/security/`

## Monitoring Documentation
- List available dashboards and their purpose
- Document key metrics and their meaning
- Explain alert conditions and thresholds
- Describe log aggregation and searching
- Include monitoring architecture diagram
- Place monitoring documentation alongside source (e.g., `monitoring/controllers/<component>/README.md`) and add optional high-level pointers in `/docs` when needed

## Code Examples
- Provide examples for common patterns
- Show both base configuration and overlays
- Include complete working examples
- Demonstrate variable substitution usage
- Show secret management patterns
- Illustrate dependency declarations
- Keep examples minimal and link to source manifests; do not duplicate full YAML blocks

## Versioning and Compatibility
- Document supported Kubernetes versions
- List Flux component versions used
- Note Helm chart version compatibility
- Document API version requirements
- Include upgrade path guidance

## Troubleshooting Guides
- Document common error messages and solutions
- Provide debugging commands and procedures
- List useful kubectl and flux commands
- Include log inspection techniques
- Describe health check validation steps
- Place troubleshooting guides under `/docs/troubleshooting/`

## External References
- Link to official Kubernetes documentation
- Reference Flux CD documentation appropriately
- Cite Helm best practices documentation
- Link to chart repositories and sources
- Reference security guidelines and standards

## Documentation Maintenance

### Quarterly Review Checklist
- [ ] Review documentation for accuracy
- [ ] Remove outdated information
- [ ] Update examples when patterns change
- [ ] Validate all commands and procedures work
- [ ] Collect feedback from documentation users
- [ ] Maintain topic indexes and navigation
- [ ] Verify `.github/instructions/` files reference (not duplicate) `/docs/`
- [ ] Ensure code-adjacent docs remain in source directories

### When Adding New Documentation

**Standards document** (`/docs/standards/`):
1. Define rules, principles, conventions
2. Include decision trees and anti-patterns
3. Provide quick reference templates
4. Update `/docs/standards/README.md` index
5. Link from `.github/instructions/` files (do not duplicate)

**Runbook** (`/docs/runbooks/`):
1. Write complete step-by-step procedure
2. Include prerequisites, validation, troubleshooting
3. Test all commands work as documented
4. Add to `/docs/runbooks/README.md` with category
5. Reference from relevant `.github/prompts/` files

**Agent instructions** (`.github/instructions/`):
1. Focus on coding patterns and conventions
2. Reference (don't duplicate) relevant `/docs/` pages
3. Include quick reference templates only
4. Link to detailed standards and runbooks
5. Update when coding patterns change, not when procedures change

**Agent prompt** (`.github/prompts/`):
1. Define agent task and workflow
2. Reference detailed runbook for procedures
3. Highlight key principles and validation
4. Provide minimal templates as quick reference
5. Link to all relevant standards and instructions

### Separation of Concerns Checklist

Before committing documentation changes:

- [ ] **Standards** define rules and principles (not step-by-step how-to)
- [ ] **Runbooks** provide complete procedures (not just principles)
- [ ] **Instructions** guide agent coding (not comprehensive docs)
- [ ] **Prompts** reference runbooks (not duplicate procedures)
- [ ] No step-by-step procedures in `.github/` files
- [ ] No comprehensive standards in `.github/` files
- [ ] No agent-specific content in `/docs/` files
- [ ] All cross-references go from `.github/` → `/docs/` (not reverse)
- [ ] Each piece of information has exactly one authoritative home

## Comment Standards
```yaml
# High-level explanation of the resource purpose
apiVersion: v1
kind: ConfigMap
metadata:
  name: example
  # NOTE: This annotation is required for Flux tracking
  annotations:
    config.kubernetes.io/origin: flux-system
data:
  # Environment-specific value substituted by Flux
  ENVIRONMENT: ${ENVIRONMENT}
  # Connection timeout in seconds
  TIMEOUT: "30"
```

## Markdown Formatting
- Use ATX-style headers (`#` not underlines)
- Use fenced code blocks with language identifiers
- Include alt text for images
- Use tables for structured data
- Use lists for sequential or grouped items
- Link to other documentation files using relative paths under `/docs`
