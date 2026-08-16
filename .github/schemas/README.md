# Local kubeconform schemas

These schemas are checked-in quality policy. They are resolved by kubeconform before
the commit-pinned Datree CRD catalog and must stay in a policy-only pull request;
they must never be combined with manifests or functions being evaluated.

## Native `CustomResourceDefinition`

`apiextensions.k8s.io/customresourcedefinition_v1.json` validates Kubernetes'
**native** `apiextensions.k8s.io/v1` `CustomResourceDefinition` objects. It is not
a schema for instances of a custom resource.

- Kubernetes source: `v1.36.3` tag, commit
  `0f29094e5b73085e3802ecc1298ecae13866bfe6` from `kubernetes/kubernetes`.
- OpenAPI source:
  `api/openapi-spec/v3/apis__apiextensions.k8s.io__v1_openapi.json`.
- Downloaded source SHA-256:
  `1c7dd621bece6661867bcc29471f774a46b36c02567d59815c7c72f6d08aa512`.
- Derived schema SHA-256:
  `b46e9288428b0396a37e7695a6aa191a0693d90e543106b9aa7f31cddd9a60c4`.

The generator `scripts/ci/generate_native_crd_schema.py` retains the OpenAPI
component schemas and their local references, makes the artifact self-contained and
offline, and closes the top-level Kubernetes object envelope. The envelope requires
`apiVersion`, `kind`, `metadata`, and `spec`; it permits optional `status`; and it
rejects unknown top-level fields under kubeconform `-strict`.

Reproduce the artifact without committing the downloaded OpenAPI input:

```bash
curl --fail --silent --show-error --location \
  https://raw.githubusercontent.com/kubernetes/kubernetes/v1.36.3/api/openapi-spec/v3/apis__apiextensions.k8s.io__v1_openapi.json \
  --output /tmp/apis__apiextensions.k8s.io__v1_openapi.json
sha256sum /tmp/apis__apiextensions.k8s.io__v1_openapi.json
python3 scripts/ci/generate_native_crd_schema.py \
  --source /tmp/apis__apiextensions.k8s.io__v1_openapi.json \
  --output .github/schemas/apiextensions.k8s.io/customresourcedefinition_v1.json
(cd .github/schemas && sha256sum --check --strict SHA256SUMS)
```

Do not use `openapi2jsonschema.py` for this artifact. That converter starts with a
CRD and derives the schema of **custom-resource instances**; this file validates the
Kubernetes `CustomResourceDefinition` object itself.
