---
applyTo: "**/kustomization.yaml"
description: "Kustomize overlay patterns for environment management"
---

# Kustomize Best Practices

## General Principles
- Use base/overlay pattern for environment separation
- Keep base configurations minimal and reusable
- Apply environment-specific patches in overlays
- Avoid duplicating resources across environments
- Use strategic merge patches for targeted modifications

## Directory Structure
Follow the standard pattern:
```
apps/
├── base/
│   └── app-name/
│       ├── kustomization.yaml
│       ├── namespace.yaml
│       ├── release.yaml
│       └── ...
└── kyrion/  # Environment overlay
    ├── kustomization.yaml
    ├── app-name-patch.yaml
    └── ...
```

## Base Configuration
- Define common resources shared across all environments
- Include namespace definitions
- Add standard labels and annotations
- Reference HelmReleases or raw manifests
- Set default resource specifications

## Overlay Configuration
- Reference base resources in `resources` field
- Apply patches for environment-specific changes
- Override values using strategic merge or JSON patches
- Add environment-specific secrets and configs
- Include additional resources unique to the environment

## Patch Strategies

### Strategic Merge Patch
Use for simple value overrides:
```yaml
patches:
  - patch: |-
      apiVersion: v1
      kind: ConfigMap
      metadata:
        name: app-config
      data:
        ENV: production
```

### JSON Patch
Use for precise modifications:
```yaml
patches:
  - target:
      kind: HelmRelease
      name: app
    patch: |
      - op: replace
        path: /spec/values/replicas
        value: 3
```

## Resource Management
- List all resources explicitly in `resources` field
- Use `bases` or `resources` to reference other kustomizations
- Apply namespace to all resources with `namespace` field
- Add common labels with `commonLabels`
- Add common annotations with `commonAnnotations`

## ConfigMap and Secret Generation
- Use `configMapGenerator` for generated ConfigMaps
- Use `secretGenerator` for generated Secrets
- Set `generatorOptions` for naming strategies
- Leverage file sources for large configurations
- Use literal sources for simple key-value pairs

## Name Prefixes and Suffixes
- Use `namePrefix` for environment identification
- Use `nameSuffix` for version or variant identification
- Apply prefixes/suffixes consistently
- Consider impact on references and selectors

## Label and Annotation Management
- Add standard Kubernetes labels to all resources
- Use `commonLabels` for selector labels (use cautiously)
- Use `commonAnnotations` for non-selector metadata
- Include Flux tracking labels automatically
- Add environment and app identification labels

## Variable Substitution
- Define variables in `vars` field
- Reference variables using `$(VAR_NAME)` syntax
- Use `fieldref` for referencing other resource fields
- Combine with Flux postBuild substitution

## Image Transformation
- Use `images` field for image tag overrides
- Specify `newName` for registry changes
- Use `newTag` for version updates
- Support digest-based image references
- Enable automatic image updates with Flux

## Component Pattern
- Create reusable components for common patterns
- Reference components in overlays
- Use components for optional features
- Keep components self-contained

## Validation
- Run `kustomize build` locally before committing
- Use `kubectl apply --dry-run=client` for validation
- Check for resource conflicts and duplicates
- Verify label selector consistency
- Test with `flux build kustomization`

## Performance Considerations
- Minimize patch complexity for faster builds
- Use strategic merge over JSON patches when possible
- Avoid excessive nesting of kustomizations
- Keep bases focused and minimal
- Limit use of generators for large datasets

## Best Practices
- Document patches with inline comments
- Group related resources in the same base
- Use consistent naming conventions
- Test overlays independently
- Keep kustomization.yaml files readable and organized
- Use `replacements` field for cross-resource references
- Leverage Kustomize built-in transformers when possible
