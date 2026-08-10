# Infrastructure Organization Standard

This standard defines how the shared platform catalog is organized, configured for a cluster, and reconciled by Flux. It is authoritative for `infrastructure/` and its cluster parameter wrappers.

## The two decisions

Classify every infrastructure change in this order:

1. **Who owns the resource and when must it be ready?**
2. **Which value does the same resource need for this cluster?**

Do not answer the second question by changing the infrastructure catalog. All clusters apply the same controllers, configuration bundles, resources, and namespaces. Only parameter values and encrypted credential material vary by cluster.

This is intentionally different from applications: `apps/<cluster>/` selects application workloads and their namespaces, while `clusters/<cluster>/infrastructure/` must not select, add, remove, or relocate infrastructure components.

## Readiness and ownership

```text
infra-controllers (Ready) -> infra-configs (Ready) -> apps
                                                    -> monitoring controllers/configs
```

- `infrastructure/controllers/<component>/` owns the resources that install and operate a platform controller: its dedicated Flux source, HelmRelease or remote Kustomization, namespace, CRD policy, and direct installation prerequisites.
- `infrastructure/configs/<component-or-domain>/` owns custom resources and configuration that require that API/controller to be available: issuers, certificates, connectors, plans, policies, and platform settings.
- The aggregate Flux Kustomizations keep `infra-configs` dependent on `infra-controllers` and use `wait: true`. Do not create a new Flux layer merely to order files.
- Use `HelmRelease.spec.dependsOn` only where one release requires another controller, CRD, or webhook to be Ready. Do not use it as a file ordering substitute.
- A resource has one Git owner. Do not duplicate a Namespace, source, CRD, Secret, or RBAC object across controller, config, or app directories.

### Classification table

| Resource or concern | Home | Rule |
|---|---|---|
| Operator/controller, dedicated source, HelmRelease, controller namespace | `infrastructure/controllers/<component>/` | Source remains beside its first and only consumer unless it is genuinely shared. |
| Controller custom resources and configuration | `infrastructure/configs/<component-or-domain>/` | Requires the controller layer to be Ready first. |
| Shared Flux source | `infrastructure/configs/flux/` | Centralize only when there is real shared ownership; do not create a global source phase. |
| Cluster networking or foundational setting | `infrastructure/configs/networking/` or `cluster-core/` | Group by operational domain, not YAML kind. |
| CI platform workload configuration | `infrastructure/configs/ci/` | ARC runner sets are controller configuration, not user applications. |
| Namespace, RBAC, ServiceAccount | The owning controller/config bundle | Keep explicit; do not rely on implicit namespace creation for platform ownership. |
| CRD lifecycle | The controller bundle that owns it | Document whether Helm/Flux uses `Create`, `CreateReplace`, or `Skip`. Treat changes to that policy as a separate migration. |

A multi-document YAML file is permitted only for resources with the same owner and lifecycle. Otherwise, split it into resource-specific files.

## Shared base and cluster parameter wrapper

```text
infrastructure/
  controllers/                           # complete shared controller catalog
  configs/                               # complete shared configuration catalog
clusters/<cluster>/
  infrastructure/
    controllers/kustomization.yaml       # includes all shared controllers + parameter artifacts
    configs/kustomization.yaml           # includes all shared configs + value-only patches
```

Each wrapper must include the complete corresponding base. It may only:

- add mandatory parameter artifacts with the same name, namespace, and keys for every cluster;
- patch scalar or structured values on an existing resource; and
- provide non-sensitive cluster values through a ConfigMap or sensitive values through a SealedSecret.

A wrapper must **not** select components, omit manifests, change `metadata.name` or `metadata.namespace`, use `namePrefix`/`nameSuffix`, or add functional infrastructure resources. A structural difference is an architecture decision outside this model, not an overlay convenience.

The Flux objects retain their identities and readiness relationship; only their `spec.path` points to `clusters/<cluster>/infrastructure/{controllers,configs}`.

## Secret and value delivery

Choose the narrowest native mechanism supported by the consumer, in this order:

1. A Kubernetes or custom-resource `secretRef`, `secretKeyRef`, or equivalent native field.
2. `HelmRelease.spec.valuesFrom` with `valuesKey` and `targetPath`.
3. A cluster wrapper patch or ConfigMap for a non-sensitive value.
4. Flux `postBuild.substituteFrom` only when a raw manifest must interpolate or compose an identifier and cannot reference a value natively.

`postBuild.substituteFrom` is not a credential-delivery mechanism. In this repository it is retained for encrypted, raw identifier composition such as `DOMAIN`, `PRIVATE_DOMAIN`, and the ACME contact field in `Certificate`, `ClusterIssuer`, DNS, hostname, or URL fields. It must not be used just because a Helm chart value is convenient to template.

Use a SealedSecret in the relevant parameter wrapper for credential values consumed by an infrastructure HelmRelease or native Secret reference. The object name, namespace, and key contract must be identical across clusters, but its ciphertext is generated with the destination cluster's sealing certificate.

### SealedSecret portability

A SealedSecret ciphertext is tied to the Sealed Secrets controller key that decrypts it. Never copy ciphertext to an independently keyed cluster. Read the existing Secret using approved Kubernetes access, re-create the same name/namespace/key contract, and seal it with the destination cluster certificate. This preserves values without inventing or rotating credentials.

Never commit plaintext credentials, private domains, internal addresses, topology, or secret values in patches, ConfigMaps, documentation, or commit messages.

## Adding or changing infrastructure

Follow [Adding an infrastructure component](../runbooks/add-infrastructure-component.md). Before changing a component, identify its owner, readiness dependency, CRD policy, source ownership, direct Secret consumers, and cluster parameters. Render the shared base and the current cluster wrappers before merging.

## Validation and rollback

Run the smallest relevant renders first, then the Flux build and YAML lint:

```bash
kustomize build infrastructure/controllers
kustomize build infrastructure/configs
kustomize build clusters/kyrion/infrastructure/controllers
kustomize build clusters/kyrion/infrastructure/configs
flux build kustomization apps --path clusters/kyrion
yamllint .
git diff --check
```

For a secret migration, compare only metadata, key names, and hashes of live data—never print values. Confirm the materialized Secret and consuming HelmRelease/CR become Ready after Flux reconciles.

A directory reorganization is a no-op only when rendered resource identity and behavior remain unchanged. If reconciliation fails, revert the Git change or suspend the affected Flux Kustomization according to the operational runbook; do not delete CRDs or namespaces as a rollback shortcut.
