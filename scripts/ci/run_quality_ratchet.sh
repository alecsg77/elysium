#!/usr/bin/env bash
# Run a trusted base/head quality comparison without embedding control flow in a workflow.
# This helper is invoked from base/scripts/ci by PR Gate; proposed content is input data only.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_quality_ratchet.sh --tool yamllint|kubeconform \
    --base-root DIRECTORY --head-root DIRECTORY \
    --base-sha SHA --head-sha SHA --report-dir DIRECTORY \
    [--base-config FILE] [--head-config FILE] [--head-scan-root DIRECTORY] \
    [--github-summary FILE] [--schema-location LOCATION]... \
    [--base-schema-location LOCATION]... [--head-schema-location LOCATION]... \
    [--reject-removed]

Both scans use this helper and the supplied trusted configuration paths. Repeated
--schema-location options apply to both kubeconform scans in the given order. A
policy comparison may instead supply distinct base/head schema locations while
scanning trusted base content with proposed policy data as inert input.
EOF
}

tool=""
base_root=""
head_root=""
base_sha=""
head_sha=""
report_dir=""
github_summary=""
schema_locations=()
base_schema_locations=()
head_schema_locations=()
base_config=""
head_config=""
head_scan_root=""
reject_removed=false

while (($#)); do
  case "$1" in
    --tool)
      tool="$2"
      shift 2
      ;;
    --base-root)
      base_root="$2"
      shift 2
      ;;
    --head-root)
      head_root="$2"
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
    --base-config)
      base_config="$2"
      shift 2
      ;;
    --head-config)
      head_config="$2"
      shift 2
      ;;
    --head-scan-root)
      head_scan_root="$2"
      shift 2
      ;;
    --reject-removed)
      reject_removed=true
      shift
      ;;
    --github-summary)
      github_summary="$2"
      shift 2
      ;;
    --schema-location)
      schema_locations+=("$2")
      shift 2
      ;;
    --base-schema-location)
      base_schema_locations+=("$2")
      shift 2
      ;;
    --head-schema-location)
      head_schema_locations+=("$2")
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

case "$tool" in
  yamllint|kubeconform) ;;
  *)
    usage >&2
    exit 2
    ;;
esac

for required in base_root head_root base_sha head_sha report_dir; do
  test -n "${!required}" || {
    echo "Missing required option --${required//_/-}" >&2
    usage >&2
    exit 2
  }
done

test -d "$base_root"
test -d "$head_root"
if [ -z "$head_scan_root" ]; then
  head_scan_root="$head_root"
fi
test -d "$head_scan_root"
mkdir -p "$report_dir"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
comparator="$script_dir/quality_ratchet.py"
test -f "$comparator"

scan_yamllint() {
  local tree="$1"
  local configuration="$2"
  local report="$3"
  local exit_code

  set +e
  (
    cd "$tree"
    yamllint -c "$configuration" -f parsable clusters infrastructure apps monitoring functions
  ) >"$report" 2>"$report.stderr"
  exit_code=$?
  set -e

  if [ -s "$report.stderr" ]; then
    cat "$report.stderr" >&2
    echo "yamllint emitted stderr instead of a trusted parsable report." >&2
    exit 1
  fi
  case "$exit_code" in
    0|1) ;;
    *)
      echo "yamllint exited unexpectedly with $exit_code." >&2
      exit "$exit_code"
      ;;
  esac
  printf '%s' "$exit_code"
}

scan_kubeconform() {
  local rendered="$1"
  local report="$2"
  shift 2
  local -a locations=("$@")
  local -a command=(
    kubeconform
    -strict
    -output json
    -summary
    -schema-location default
  )
  local location
  local exit_code

  for location in "${locations[@]}"; do
    test -n "$location" || {
      echo "kubeconform schema locations must not be empty." >&2
      exit 2
    }
    command+=(-schema-location "$location")
  done

  set +e
  "${command[@]}" "$rendered" >"$report" 2>"$report.stderr"
  exit_code=$?
  set -e

  if [ -s "$report.stderr" ]; then
    cat "$report.stderr" >&2
    echo "kubeconform emitted stderr instead of a trusted JSON report." >&2
    exit 1
  fi
  case "$exit_code" in
    0|1) ;;
    *)
      echo "kubeconform exited unexpectedly with $exit_code." >&2
      exit "$exit_code"
      ;;
  esac
  printf '%s' "$exit_code"
}

case "$tool" in
  yamllint)
    if [ -z "$base_config" ]; then
      base_config="$base_root/.yamllint.yaml"
    fi
    if [ -z "$head_config" ]; then
      head_config="$base_config"
    fi
    test -f "$base_config"
    test -f "$head_config"
    base_exit="$(scan_yamllint "$base_root" "$base_config" "$report_dir/base-yamllint.txt")"
    head_exit="$(scan_yamllint "$head_scan_root" "$head_config" "$report_dir/head-yamllint.txt")"
    base_report="$report_dir/base-yamllint.txt"
    head_report="$report_dir/head-yamllint.txt"
    output_report="$report_dir/quality-yamllint.json"
    root_options=(--base-root "$base_root" --head-root "$head_scan_root")
    ;;
  kubeconform)
    if ((${#schema_locations[@]})); then
      if ((${#base_schema_locations[@]} || ${#head_schema_locations[@]})); then
        echo "Use either --schema-location or both --base-schema-location and --head-schema-location." >&2
        exit 2
      fi
      base_schema_locations=("${schema_locations[@]}")
      head_schema_locations=("${schema_locations[@]}")
    fi
    if ((${#base_schema_locations[@]} == 0 || ${#head_schema_locations[@]} == 0)); then
      echo "kubeconform requires --schema-location or both base/head schema locations." >&2
      exit 2
    fi
    base_exit="$(scan_kubeconform "$base_root" "$report_dir/base-kubeconform.json" "${base_schema_locations[@]}")"
    head_exit="$(scan_kubeconform "$head_root" "$report_dir/head-kubeconform.json" "${head_schema_locations[@]}")"
    base_report="$report_dir/base-kubeconform.json"
    head_report="$report_dir/head-kubeconform.json"
    output_report="$report_dir/quality-kubeconform.json"
    root_options=()
    ;;
esac

arguments=(
  --tool "$tool"
  --base-report "$base_report"
  --head-report "$head_report"
  --base-sha "$base_sha"
  --head-sha "$head_sha"
  --base-exit-code "$base_exit"
  --head-exit-code "$head_exit"
  --report "$output_report"
  --github-annotations
  "${root_options[@]}"
)
if [ "$reject_removed" = true ]; then
  arguments+=(--reject-removed)
fi
if [ -n "$github_summary" ]; then
  arguments+=(--github-summary "$github_summary")
fi
python3 "$comparator" "${arguments[@]}"
