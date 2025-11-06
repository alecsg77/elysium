---
applyTo: "**/*.md,**/*.yaml,**/*.yml"
description: "Documentation standards for GitOps repository"
---

# Documentation Standards

## General Guidelines
- Keep documentation close to code (in-directory README files)
- Use clear, concise language accessible to team members
- Update documentation alongside code changes
- Include practical examples for complex patterns
- Link to official documentation for third-party tools

## README Structure
Each major directory should have a README.md with:
- **Overview**: Brief description of the directory's purpose
- **Contents**: List of key files and subdirectories
- **Usage**: How to deploy or interact with resources
- **Dependencies**: Required components or prerequisites
- **Configuration**: Key configuration options and variables
- **Examples**: Common use cases and patterns
- **Troubleshooting**: Known issues and solutions

## Inline Documentation
- Add YAML comments for non-obvious configuration choices
- Document why specific values or patterns are used
- Explain dependency relationships and ordering
- Note any workarounds or temporary solutions
- Reference relevant issues or documentation links

## Application Documentation
For each application in `apps/base/<app>/`:
- Document application purpose and functionality
- List exposed services and ingress endpoints
- Describe configuration options and customization
- Include upgrade and rollback procedures
- Note resource requirements and scaling considerations
- Document backup and restore procedures

## Architecture Documentation
Maintain high-level architecture documentation:
- Cluster topology and node roles
- Network architecture and service mesh
- Storage architecture and PVC management
- Security boundaries and access controls
- Monitoring and observability stack
- Disaster recovery procedures

## Change Documentation
- Use descriptive Git commit messages
- Follow conventional commits format
- Document breaking changes prominently
- Include migration guides for major changes
- Link commits to related issues or PRs
- Tag releases with comprehensive changelogs

## Runbook Documentation
Create runbooks for common operational tasks:
- Cluster bootstrap and initialization
- Adding new applications or services
- Secret rotation procedures
- Scaling applications up or down
- Troubleshooting common issues
- Disaster recovery procedures

## Diagram Standards
- Use mermaid diagrams for architecture visualization
- Embed diagrams in markdown files
- Keep diagrams simple and focused
- Update diagrams when architecture changes
- Include dependency flow diagrams
- Document network topology visually

## API and Interface Documentation
- Document custom CRDs with examples
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

## Monitoring Documentation
- List available dashboards and their purpose
- Document key metrics and their meaning
- Explain alert conditions and thresholds
- Describe log aggregation and searching
- Include monitoring architecture diagram

## Code Examples
- Provide examples for common patterns
- Show both base configuration and overlays
- Include complete working examples
- Demonstrate variable substitution usage
- Show secret management patterns
- Illustrate dependency declarations

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

## External References
- Link to official Kubernetes documentation
- Reference Flux CD documentation appropriately
- Cite Helm best practices documentation
- Link to chart repositories and sources
- Reference security guidelines and standards

## Documentation Maintenance
- Review documentation quarterly for accuracy
- Remove outdated information promptly
- Update examples when patterns change
- Validate commands and procedures work
- Collect feedback from documentation users

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
- Link to other documentation files using relative paths
