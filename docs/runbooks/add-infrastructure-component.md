# Adding or Changing an Infrastructure Component

Use this runbook when introducing or changing a platform controller, its cluster-wide configuration, or the parameters that make the shared infrastructure catalog work on a cluster.

For placement rules, read the [Infrastructure organization standard](../standards/infrastructure-organization.md) first.

## Prerequisites

- Git access to this repository.
- `kustomize`, `flux`, `yamllint`, `kubectl`, and `kubeseal`.
- Approved Kubernetes read access when an existing Secret must be re-sealed. Do not print secret values.
- The public sealing certificate for the destination cluster, for example `etc/certs/pub-sealed-secrets.pem` for the current cluster.

## 1. Classify the change

Answer these questions before creating files:

1. Does the resource install an API, CRD, webhook, or controller? Put the controller bundle in `infrastructure/controllers/<component>/`.
2. Is it a custom resource or platform setting consumed after that controller exists? Put it in `infrastructure/configs/<component-or-domain>/`.
3. Is the value identical on all clusters? Keep it in the shared base.
4. Does the same resource need a different scalar, credential, hostname, domain, CIDR, endpoint, capacity, or feature value per cluster? Use the corresponding `clusters/<cluster>/infrastructure/` wrapper.

Do not use a cluster wrapper to choose controllers, remove configs, or change namespaces. Application selection belongs in `apps/<cluster>/`.

## 2. Add a controller bundle

Create a component directory with an explicit `kustomization.yaml`. Keep its dedicated source, release, namespace, and installation prerequisites together.

```text
infrastructure/controllers/<component>/
├── kustomization.yaml
├── namespace.yaml            # when the controller owns an explicit namespace
├── repository.yaml           # dedicated HelmRepository/OCIRepository/GitRepository
└── release.yaml              # HelmRelease or controller Kustomization
```

Document the CRD lifecycle choice in the component README or release comments:

- `Create` for installation when chart-managed CRDs are created.
- `CreateReplace` only after an explicit compatibility review and rollback plan.
- `Skip` when a distinct, authoritative CRD bundle manages them.

If another HelmRelease creates CRs or calls a webhook exposed by this controller, add a `HelmRelease.spec.dependsOn`. Otherwise, rely on the aggregate `infra-configs -> infra-controllers` readiness boundary.

## 3. Add controller configuration

Place post-install custom resources in a matching configuration domain:

```text
infrastructure/configs/<component-or-domain>/
├── kustomization.yaml
└── <resource>.yaml
```

Do not place configuration CRs beside the controller merely because they share a Kubernetes kind or vendor.

## 4. Deliver parameters and secrets correctly

Use the narrowest supported mechanism:

1. Native `secretRef` / `secretKeyRef` on a resource or CR.
2. HelmRelease `valuesFrom` with a SealedSecret or ConfigMap.
3. Wrapper patch for a non-sensitive value.
4. `postBuild.substituteFrom` only for raw string composition with no native reference option.

For a new credential, create a SealedSecret in the matching cluster wrapper. Preserve the exact Secret name, namespace, and data keys expected by the consumer on every cluster.

```bash
# Read an existing Secret without printing its values, transform only its data keys,
# and seal the replacement for the current cluster.
kubectl -n <namespace> get secret <name> -o json \
  | jq '{apiVersion:"v1",kind:"Secret",metadata:{name:"<name>",namespace:"<namespace>"},type:"Opaque",data:{"<key>":.data["<source-key>"]}}' \
  | kubeseal --cert etc/certs/pub-sealed-secrets.pem --format yaml \
  > clusters/kyrion/infrastructure/<layer>/<component>-sealed-secret.yaml
```

Review the generated manifest for name, namespace, and encrypted data key names only. Do not redirect a decoded Secret value to the terminal or commit it.

## 5. Wire the current cluster wrapper

The current cluster wrapper includes the complete shared base and only supplies parameter artifacts and patches:

```text
clusters/kyrion/infrastructure/
├── controllers/kustomization.yaml
└── configs/kustomization.yaml
```

Add a SealedSecret or ConfigMap to the matching wrapper only when it is a required parameter artifact for the same shared resource on every cluster. Keep cluster-specific patches close to the wrapper, not inline in the Flux Kustomization in `clusters/kyrion/infrastructure.yaml`.

## 6. Validate before merge

```bash
kustomize build infrastructure/controllers
kustomize build infrastructure/configs
kustomize build clusters/kyrion/infrastructure/controllers
kustomize build clusters/kyrion/infrastructure/configs
flux build kustomization apps --path clusters/kyrion
yamllint .
git diff --check
```

For controller changes, also render the owning component and inspect Flux dependencies. For a secret migration, compare live data hashes only and verify that the expected Secret name and keys are present after reconciliation.

## 7. Reconcile and verify

After the Git change is merged and Flux has fetched it:

```bash
flux reconcile kustomization infra-controllers --with-source
flux reconcile kustomization infra-configs --with-source
flux get kustomizations
flux get helmreleases -A
```

Verify the controller reaches Ready before checking the configuration CRs it owns. For secret-backed HelmRelease values, verify the materialized Secret exists in the HelmRelease namespace and then inspect HelmRelease readiness.

## Rollback

Revert the Git commit that changed the component or parameter wrapper. Do not delete a CRD, namespace, or live Secret to force reconciliation. If necessary, suspend only the affected Flux Kustomization while investigating the first failing resource.

## Checklist

- [ ] Controller/config owner identified.
- [ ] Source ownership and namespace are explicit.
- [ ] CRD policy is reviewed and documented.
- [ ] No duplicate Git owner was introduced.
- [ ] Cluster wrapper changes parameters only; it does not select components.
- [ ] Credentials use native Secret references or `valuesFrom`.
- [ ] No plaintext secret or sensitive identifier was added.
- [ ] Required renders, Flux build, lint, and diff checks passed.
