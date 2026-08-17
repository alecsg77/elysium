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

## K8up `Schedule`

`k8up.io/schedule_v1.json` validates `k8up.io/v1` `Schedule` resources against
the CRD shipped by the installed K8up version. The local schema takes precedence
over the older commit-pinned Datree catalog entry, which does not include the
`backup.labelSelectors` field added upstream.

- K8up source: `k8up-4.10.0` tag, commit
  `162266842bf4ce20d5b6296d14701cf46c2de8bb` from `k8up-io/k8up`.
- CRD source: `charts/k8up/crds/k8up.io_schedules.yaml`.
- Downloaded CRD SHA-256:
  `4821bf5c432d40baebec890e3c5c7fae899bb203089c4604492ac008a31d918e`.
- Derived schema SHA-256:
  `fac8496b174a184ef1096deff82197d87e887006c73b736db06e1c8abb132e9a`.

The artifact is the canonical, key-sorted JSON representation of
`.spec.versions[name == "v1"].schema.openAPIV3Schema` from that CRD. Reproduce it
without committing the downloaded YAML input:

```bash
curl --fail --silent --show-error --location \
  https://raw.githubusercontent.com/k8up-io/k8up/162266842bf4ce20d5b6296d14701cf46c2de8bb/charts/k8up/crds/k8up.io_schedules.yaml \
  --output /tmp/k8up.io_schedules.yaml
sha256sum /tmp/k8up.io_schedules.yaml
python3 - <<'PY'
import json

import yaml

with open("/tmp/k8up.io_schedules.yaml", encoding="utf-8") as source:
    crd = yaml.safe_load(source)

schema = next(
    version["schema"]["openAPIV3Schema"]
    for version in crd["spec"]["versions"]
    if version["name"] == "v1"
)
with open(".github/schemas/k8up.io/schedule_v1.json", "w", encoding="utf-8") as output:
    json.dump(schema, output, indent=2, sort_keys=True, ensure_ascii=False)
    output.write("\n")
PY
(cd .github/schemas && sha256sum --check --strict SHA256SUMS)
```
