#!/usr/bin/env bash
set -euo pipefail

repo_root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
fixture=$(mktemp -d)
trap 'rm -rf -- "$fixture"' EXIT
mkdir -p "$fixture/bin"
cat >"$fixture/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "$TAG_SCENARIO" in
  identical) printf '{"config":{"Labels":{"dev.elysium.build-inputs":"%s"}}}\n' "$EXPECTED_INPUT_HASH" ;;
  identical_index)
    printf '{"linux/amd64":{"config":{"Labels":{"dev.elysium.build-inputs":"%s"}}}}\n' "$EXPECTED_INPUT_HASH"
    ;;
  collision) echo '{"config":{"Labels":{}}}' ;;
  index_collision) echo '{"linux/amd64":{"config":{"Labels":{}}}}' ;;
  missing) echo 'ERROR: registry.example.com/image:1.0.0: not found' >&2; exit 1 ;;
  denied) echo 'ERROR: unexpected status: 401 Unauthorized' >&2; exit 1 ;;
  network) echo 'ERROR: dial tcp: i/o timeout' >&2; exit 1 ;;
  malformed) echo 'invalid JSON' ;;
esac
EOF
chmod +x "$fixture/bin/docker"
export PATH="$fixture/bin:$PATH"
export EXPECTED_INPUT_HASH=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

for TAG_SCENARIO in identical identical_index missing collision index_collision denied network malformed; do
  export TAG_SCENARIO
  result=0
  bash "$repo_root/scripts/ci/check-image-tag.sh" \
    --image registry.example.com/image:1.0.0 --input-hash "$EXPECTED_INPUT_HASH" \
    --output "$fixture/needed" >"$fixture/stdout" 2>"$fixture/stderr" || result=$?
  case "$TAG_SCENARIO" in
    identical|identical_index) test "$result" -eq 0; grep -qx false "$fixture/needed" ;;
    missing) test "$result" -eq 0; grep -qx true "$fixture/needed" ;;
    *) test "$result" -ne 0 ;;
  esac
done
echo 'Image registry checks passed (8 scenarios).'
