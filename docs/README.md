# Elysium Documentation

Centralized documentation for the Elysium GitOps-managed Kubernetes homelab. Use the topic indexes below.

## Topics
- **[Architecture](architecture/README.md)** - Cluster topology, network design, storage architecture, and security boundaries
- **[Standards](standards/README.md)** - Repository structure, coding standards, and best practices
  - **[Repository Structure](standards/repository-structure.md)** - Authoritative guide to monorepo organization
- **[Security](security/README.md)** - Secret management, RBAC policies, and incident response
- **[Runbooks](runbooks/README.md)** - Operational procedures and step-by-step guides
  - **[Adding Applications](runbooks/add-application.md)** - Complete workflow for deploying apps
  - **[Resource Optimization](runbooks/resource-optimization.md)** - Optimizing cluster resources
- **[Troubleshooting](troubleshooting/README.md)** - Diagnostic workflows, known issues, and solutions

## Conventions
- General project documentation lives under `/docs`
- Code-adjacent documentation (apps, infrastructure, monitoring, templates, functions, scripts) stays alongside sources
- Keep examples minimal; link to code files in their source folders
- Use relative links within `/docs` for general docs
