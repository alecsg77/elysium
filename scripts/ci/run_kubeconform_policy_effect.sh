#!/usr/bin/env bash
# Compare trusted rendered input under base and proposed kubeconform schema policy.
# The proposed workflow and schemas are parsed/scanned only as inert data.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_kubeconform_policy_effect.sh --rendered-root DIRECTORY \
    --base-schemas-root DIRECTORY --base-catalog-commit SHA \
    --candidate-workflow FILE --candidate-schemas-root DIRECTORY \
    --base-sha SHA --head-sha SHA --report-dir DIRECTORY \
    [--github-summary FILE]
EOF
}

rendered_root=""
base_schemas_root=""
base_catalog_commit=""
candidate_workflow=""
candidate_schemas_root=""
base_sha=""
head_sha=""
report_dir=""
github_summary=""

while (($#)); do
  case "$1" in
    --rendered-root)
      rendered_root="$2"
      shift 2
      ;;
    --base-schemas-root)
      base_schemas_root="$2"
      shift 2
      ;;
    --base-catalog-commit)
      base_catalog_commit="$2"
      shift 2
      ;;
    --candidate-workflow)
      candidate_workflow="$2"
      shift 2
      ;;
    --candidate-schemas-root)
      candidate_schemas_root="$2"
      shift 2
      ;;
    --base-sha)
      base_sha="$2"
      shift 2
      ;;
    --head-sha)
      head_sha="$2"
      shift 2
      ;;
    --report-dir)
      report_dir="$2"
      shift 2
      ;;
    --github-summary)
      github_summary="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

for required in \
  rendered_root base_schemas_root base_catalog_commit candidate_workflow \
  candidate_schemas_root base_sha head_sha report_dir; do
  test -n "${!required}" || {
    echo "Missing required option --${required//_/-}" >&2
    usage >&2
    exit 2
  }
done

if ! [[ "$base_catalog_commit" =~ ^[0-9a-f]{40}$ ]]; then
  echo "--base-catalog-commit must be exactly a 40-character lowercase SHA." >&2
  exit 2
fi

test -d "$rendered_root"
test -f "$candidate_workflow"
if [ -e "$base_schemas_root" ]; then
  test -d "$base_schemas_root"
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
schema_template='{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'
base_catalog="https://raw.githubusercontent.com/datreeio/CRDs-catalog/${base_catalog_commit}/${schema_template}"
candidate_locations="$report_dir/candidate-schema-locations.txt"
mkdir -p "$report_dir"

if [ -d "$candidate_schemas_root" ]; then
  test -f "$candidate_schemas_root/README.md"
  test -f "$candidate_schemas_root/SHA256SUMS"
  (
    cd "$candidate_schemas_root"
    sha256sum --check --strict SHA256SUMS
  )
fi

python3 "$script_dir/resolve_kubeconform_schema_locations.py" \
  --workflow "$candidate_workflow" \
  --schemas-root "$candidate_schemas_root" \
  --output "$candidate_locations"

base_arguments=(--base-schema-location "$base_catalog")
if [ -d "$base_schemas_root" ]; then
  base_arguments=(
    --base-schema-location "$base_schemas_root/$schema_template"
    "${base_arguments[@]}"
  )
fi

head_arguments=()
candidate_kubeconform_arguments=()
while IFS= read -r location; do
  test -n "$location" || {
    echo "Candidate kubeconform schema locations must not be empty." >&2
    exit 1
  }
  head_arguments+=(--head-schema-location "$location")
  candidate_kubeconform_arguments+=(-schema-location "$location")
done < "$candidate_locations"
((${#head_arguments[@]})) || {
  echo "Candidate kubeconform schema policy produced no schema locations." >&2
  exit 1
}

native_crd_schema="$candidate_schemas_root/apiextensions.k8s.io/customresourcedefinition_v1.json"
if [ -e "$native_crd_schema" ]; then
  test -f "$native_crd_schema"
  fixture="$report_dir/invalid-native-customresourcedefinition.yaml"
  negative_report="$report_dir/invalid-native-customresourcedefinition.json"
  cat > "$fixture" <<'EOF'
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: tests.example.invalid
spec:
  group: example.invalid
  names:
    kind: Test
    plural: tests
    singular: test
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
unexpectedTopLevel: true
EOF
  set +e
  kubeconform -strict -output json -summary \
    "${candidate_kubeconform_arguments[@]}" \
    "$fixture" > "$negative_report" 2> "$negative_report.stderr"
  negative_exit=$?
  set -e
  test "$negative_exit" -eq 1 || {
    echo "Candidate native CRD schema must reject an unknown top-level property." >&2
    exit 1
  }
  test ! -s "$negative_report.stderr" || {
    sed -n '1,160p' "$negative_report.stderr" >&2
    echo "kubeconform emitted stderr while checking the native CRD negative fixture." >&2
    exit 1
  }
  python3 - "$negative_report" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
summary = payload.get("summary")
resources = payload.get("resources")
if not isinstance(summary, dict) or not isinstance(resources, list):
    raise SystemExit("Native CRD negative fixture emitted malformed kubeconform JSON.")
if summary.get("invalid") != 1 or summary.get("errors") != 0 or summary.get("skipped") != 0:
    raise SystemExit("Native CRD negative fixture did not produce exactly one invalid result.")
if len(resources) != 1 or resources[0].get("status") != "statusInvalid":
    raise SystemExit("Native CRD negative fixture was not rejected as invalid.")
PY
fi

arguments=(
  --tool kubeconform
  --base-root "$rendered_root"
  --head-root "$rendered_root"
  --base-sha "$base_sha"
  --head-sha "$head_sha"
  --report-dir "$report_dir"
  "${base_arguments[@]}"
  "${head_arguments[@]}"
)
if [ -n "$github_summary" ]; then
  arguments+=(--github-summary "$github_summary")
fi
bash "$script_dir/run_quality_ratchet.sh" "${arguments[@]}"
