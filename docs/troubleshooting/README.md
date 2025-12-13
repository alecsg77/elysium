# Troubleshooting

Guides and knowledge base for diagnosing and resolving cluster issues.

## Contents

- **[Known Issues and Troubleshooting](known-issues.md)** - Searchable KB of common problems, symptoms, root causes, and verified resolutions
- **[Web-Based Troubleshooting Workflow](web-troubleshooting.md)** - Complete guide for investigating issues via GitHub Issues and Copilot Chat from web browser
- **[Implementation Status](implementation-status.md)** - Overview of web troubleshooting system components and features
- **[Coder HelmRelease Timeout](coder-helmrelease-timeout.md)** - Specific investigation and resolution for memory-constrained upgrades

## Quick Links

### Creating Issues
- **New Issue**: https://github.com/alecsg77/elysium/issues/new/choose
- **Templates**: Bug Report, Troubleshooting Request, Feature Request

### Using Copilot Chat
```
#file:.github/agents/troubleshooter.agents.md
Please investigate this issue and run diagnostics
```

### Common Commands
- `/approve-plan` - Approve all resolution plans
- `/reject` - Request alternative approach
- `/reset-attempts` - Reset circuit breaker after manual fix

## Issue Categories

See [Known Issues](known-issues.md) for:
- Flux CD issues (HelmRelease timeouts, variable substitution, Git sync)
- Kubernetes issues (Pod crashes, ImagePull errors, resource constraints)
- Helm installation failures
- Storage and PVC issues
- Application-specific problems

## Diagnostic Process

The web-based workflow provides 5 diagnostic phases:
1. **Health Check** - System status
2. **Resource Status** - Kubernetes/Flux conditions
3. **Logs** - Error extraction
4. **Events** - Chronological timeline
5. **Configuration** - Manifests and variables

See [Web-Based Workflow](web-troubleshooting.md) for complete details.
