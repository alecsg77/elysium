# Local kubeconform schemas

These checked-in schemas are validation inputs. Kubeconform resolves them before the
commit-pinned Datree CRD catalog. Update a schema in a focused policy PR, verify its
checksum in `SHA256SUMS`, and validate the current rendered Flux surfaces before it
governs a later manifest change.

## Native `CustomResourceDefinition`

`apiextensions.k8s.io/customresourcedefinition_v1.json` validates Kubernetes'
native `apiextensions.k8s.io/v1` `CustomResourceDefinition` objects. It is not a
schema for instances of a custom resource.

- Kubernetes source: `v1.36.3` tag, commit
  `0f29094e5b73085e3802ecc1298ecae13866bfe6` from `kubernetes/kubernetes`.
- OpenAPI source:
  `api/openapi-spec/v3/apis__apiextensions.k8s.io__v1_openapi.json`.
- Downloaded source SHA-256:
  `1c7dd621bece6661867bcc29471f774a46b36c02567d59815c7c72f6d08aa512`.
- Derived schema SHA-256:
  `b46e9288428b0396a37e7695a6aa191a0693d90e543106b9aa7f31cddd9a60c4`.

The stored schema is self-contained and closes the top-level Kubernetes object
envelope: it requires `apiVersion`, `kind`, `metadata`, and `spec`, permits optional
`status`, and rejects unknown top-level fields under kubeconform `-strict`.

## K8up `Schedule`

`k8up.io/schedule_v1.json` validates `k8up.io/v1` `Schedule` resources against the
CRD shipped by the installed K8up version. The local schema takes precedence over the
older commit-pinned Datree catalog entry, which does not include the
`backup.labelSelectors` field added upstream.

- K8up source: `k8up-4.10.0` tag, commit
  `162266842bf4ce20d5b6296d14701cf46c2de8bb` from `k8up-io/k8up`.
- CRD source: `charts/k8up/crds/k8up.io_schedules.yaml`.
- Downloaded CRD SHA-256:
  `4821bf5c432d40baebec890e3c5c7fae899bb203089c4604492ac008a31d918e`.
- Derived schema SHA-256:
  `fac8496b174a184ef1096deff82197d87e887006c73b736db06e1c8abb132e9a`.

## K8up `Restore`

`k8up.io/restore_v1.json` validates `k8up.io/v1` `Restore` resources against the
CRD shipped by the installed K8up version. The local schema takes precedence over
the older commit-pinned Datree catalog entry, which does not include the `paths`
field used to select a source PVC snapshot.

- K8up source: `k8up-4.10.0` tag, commit
  `162266842bf4ce20d5b6296d14701cf46c2de8bb` from `k8up-io/k8up`.
- CRD source: `charts/k8up/crds/k8up.io_restores.yaml`.
- Downloaded CRD SHA-256:
  `32a4a2491b71667a4fcfdfe8c041bdc5e38596d3753dbae31caf8f207eab91a2`.
- Derived schema SHA-256:
  `23bec3319c917d43dfa17a95a1ed78d7930961a66c35c8652c20733784141ce0`.
