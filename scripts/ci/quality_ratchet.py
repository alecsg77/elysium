#!/usr/bin/env python3
"""Compare trusted base and proposed quality-validator findings.

The pull_request_target PR Gate invokes this helper only from its trusted base
checkout. Validator reports are data: this helper never executes PR-provided
scripts, loads PR-provided policy, or writes raw manifest content into reports.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

try:
    import yaml
except ImportError as error:  # pragma: no cover - exercised by CI dependency setup
    raise SystemExit(f"PyYAML is required by quality_ratchet.py: {error}")

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sealed_secret_ciphertext_policy import ciphertext_ranges, redact_line


class QualityRatchetError(RuntimeError):
    """Raised when a validator report is malformed or cannot be trusted."""


@dataclass(frozen=True)
class Finding:
    """A normalized, secret-safe validator finding."""

    identity: str
    display: str


YAMLLINT_PATTERN = re.compile(
    r"^(?P<path>.+?):(?P<line>[0-9]+):(?P<column>[0-9]+): "
    r"\[(?P<level>[^]]+)\] (?P<message>.*) \((?P<rule>[^()]*)\)$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", choices=("yamllint", "kubeconform", "checkov"), required=True)
    parser.add_argument("--base-report", type=Path, required=True)
    parser.add_argument("--head-report", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--github-summary", type=Path)
    parser.add_argument("--github-annotations", action="store_true")
    parser.add_argument(
        "--reject-removed",
        action="store_true",
        help="Fail when a policy comparison removes existing findings instead of remediating them.",
    )
    parser.add_argument("--base-root", type=Path)
    parser.add_argument("--head-root", type=Path)
    parser.add_argument("--base-exit-code", type=int)
    parser.add_argument("--head-exit-code", type=int)
    parser.add_argument(
        "--allowed-exit-codes",
        default="0,1",
        help="Comma-separated scanner exit codes that represent parsable findings (default: 0,1).",
    )
    return parser.parse_args()


def normalized_text(value: str) -> str:
    """Return stable text without changing meaningful non-whitespace characters."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value).strip())


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise QualityRatchetError(f"Validator report is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise QualityRatchetError(f"Validator report is not valid JSON: {path}: {error}") from error


def require_string(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise QualityRatchetError(f"{context} is missing non-empty string field {key!r}")
    return value


def safe_relative_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute() or ".." in path.parts:
        raise QualityRatchetError(f"yamllint report has unsafe path {path_text!r}")
    return path


def parse_yamllint(report: Path, root: Path | None) -> list[Finding]:
    if root is None:
        raise QualityRatchetError("yamllint parsing requires --base-root and --head-root")
    if not root.is_dir():
        raise QualityRatchetError(f"yamllint root is missing: {root}")
    try:
        lines = report.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise QualityRatchetError(f"Validator report is missing: {report}") from error

    findings: list[Finding] = []
    source_cache: dict[Path, tuple[list[str], list[Any]]] = {}
    for raw in lines:
        if not raw.strip():
            continue
        match = YAMLLINT_PATTERN.fullmatch(raw)
        if match is None:
            raise QualityRatchetError(f"Unrecognized yamllint parsable output: {raw!r}")
        relative = safe_relative_path(match.group("path"))
        source = root / relative
        if source not in source_cache:
            try:
                source_content = source.read_text(encoding="utf-8")
            except FileNotFoundError as error:
                raise QualityRatchetError(f"yamllint finding references missing source file {relative}") from error
            # Only a parsed, exact SealedSecret ciphertext scalar is normalized.
            # Malformed or ambiguous YAML returns no ranges and retains the full
            # source-line hash, so policy uncertainty cannot hide new debt.
            source_cache[source] = (source_content.splitlines(), ciphertext_ranges(source_content))
        source_lines, scalar_ranges = source_cache[source]
        line_number = int(match.group("line"))
        if not 1 <= line_number <= len(source_lines):
            raise QualityRatchetError(
                f"yamllint finding references unavailable line {line_number} in {relative}"
            )
        offending_line = unicodedata.normalize("NFC", source_lines[line_number - 1])
        if normalized_text(match.group("rule")) == "line-length":
            offending_line = redact_line(offending_line, line_number, scalar_ranges)
        message_class = normalized_text(re.sub(r"\b[0-9]+\b", "<n>", match.group("message")))
        identity = "|".join(
            (
                "v1",
                "tool=yamllint",
                f"path={relative.as_posix()}",
                f"rule={normalized_text(match.group('rule'))}",
                f"level={normalized_text(match.group('level'))}",
                f"class={message_class}",
                f"line_hash={digest(offending_line)}",
            )
        )
        findings.append(Finding(identity=identity, display=f"{relative.as_posix()} ({match.group('rule')})"))
    return findings


def load_rendered_document(
    filename: str,
    version: str,
    kind: str,
    name: str,
    cache: dict[str, dict[tuple[str, str, str], list[dict[str, Any]]]],
) -> tuple[str, str]:
    """Load a rendered resource once per artifact, then resolve it by GVK/name."""
    path = Path(filename)
    if not path.is_file():
        raise QualityRatchetError(f"kubeconform report references unavailable rendered file {filename!r}")
    if filename not in cache:
        try:
            documents = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        except (OSError, yaml.YAMLError) as error:
            raise QualityRatchetError(f"Cannot parse rendered file {filename!r}: {error}") from error
        indexed: dict[tuple[str, str, str], list[dict[str, Any]]] = collections.defaultdict(list)
        for document in documents:
            if not isinstance(document, dict):
                continue
            metadata = document.get("metadata")
            if not isinstance(metadata, dict) or not isinstance(metadata.get("name"), str):
                continue
            api_version = document.get("apiVersion")
            kind_name = document.get("kind")
            if isinstance(api_version, str) and isinstance(kind_name, str):
                indexed[(api_version, kind_name, metadata["name"])].append(document)
        cache[filename] = indexed

    matches = cache[filename].get((version, kind, name), [])
    if len(matches) != 1:
        raise QualityRatchetError(
            f"Could not uniquely map kubeconform finding {version}/{kind}/{name} in {filename!r}"
        )
    metadata = matches[0].get("metadata", {})
    namespace = metadata.get("namespace")
    if namespace is None:
        namespace = "_cluster"
    if not isinstance(namespace, str) or not namespace:
        raise QualityRatchetError(f"Rendered resource {version}/{kind}/{name} has invalid namespace")
    canonical = json.dumps(matches[0], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return namespace, digest(canonical)


def canonical_kubeconform_error(record: dict[str, Any]) -> str:
    validation_errors = record.get("validationErrors", [])
    if not isinstance(validation_errors, list):
        raise QualityRatchetError("kubeconform validationErrors must be a list")
    details: list[dict[str, str]] = []
    for error in validation_errors:
        if not isinstance(error, dict):
            raise QualityRatchetError("kubeconform validationErrors contains a non-object")
        details.append(
            {
                "path": normalized_text(str(error.get("path", ""))),
                "message": normalized_text(str(error.get("msg", ""))),
            }
        )
    if not details:
        message = record.get("msg")
        if not isinstance(message, str) or not message:
            raise QualityRatchetError("kubeconform invalid resource has no error detail")
        details.append({"path": "", "message": normalized_text(message)})
    return json.dumps(sorted(details, key=lambda item: (item["path"], item["message"])), separators=(",", ":"))


def parse_kubeconform(report: Path, _root: Path | None) -> list[Finding]:
    payload = load_json(report)
    if not isinstance(payload, dict) or not isinstance(payload.get("resources"), list):
        raise QualityRatchetError("kubeconform JSON must be an object with a resources list")

    candidates: list[tuple[str, str, str, str]] = []
    rendered_cache: dict[str, dict[tuple[str, str, str], list[dict[str, Any]]]] = {}
    for entry in payload["resources"]:
        if not isinstance(entry, dict):
            raise QualityRatchetError("kubeconform resources contains a non-object")
        status = require_string(entry, "status", "kubeconform resource")
        if status == "statusValid":
            continue
        version = require_string(entry, "version", "kubeconform resource")
        kind = require_string(entry, "kind", "kubeconform resource")
        name = require_string(entry, "name", "kubeconform resource")
        filename = require_string(entry, "filename", "kubeconform resource")
        namespace, manifest_hash = load_rendered_document(filename, version, kind, name, rendered_cache)
        message = entry.get("msg")
        if status == "statusError":
            if not isinstance(message, str) or not message.startswith("could not find schema for "):
                raise QualityRatchetError(
                    f"kubeconform reported execution/schema error for {version}/{kind}/{namespace}/{name}"
                )
            status = "statusMissingSchema"
        if status not in {"statusInvalid", "statusSkipped", "statusMissingSchema"}:
            raise QualityRatchetError(f"Unknown kubeconform resource status {status!r}")
        if status == "statusInvalid":
            reason = digest(canonical_kubeconform_error(entry))
        else:
            reason = digest(normalized_text(str(message or "schema skipped")))
        primary = "|".join(
            (
                "v1",
                "tool=kubeconform",
                f"status={status}",
                f"apiVersion={version}",
                f"kind={kind}",
                f"namespace={namespace}",
                f"name={name}",
                f"reason_hash={reason}",
            )
        )
        candidates.append((primary, manifest_hash, f"{kind}/{namespace}/{name}", status))

    findings: dict[str, Finding] = {}
    for primary, manifest_hash, display, _ in candidates:
        # Keep the content discriminator on every record. Adding or removing a sibling
        # render variant must not alter the identity of the inherited variant that remains.
        identity = f"{primary}|render_variant={manifest_hash}"
        findings[identity] = Finding(identity=identity, display=display)
    return list(findings.values())


def parse_checkov_resource(value: str) -> tuple[str, str, str, str]:
    parts = value.split(".")
    if len(parts) >= 3:
        return "unknown", parts[0], parts[-2], parts[-1]
    if len(parts) == 2:
        return "unknown", parts[0], "_cluster", parts[-1]
    if len(parts) == 1 and parts[0]:
        return "unknown", parts[0], "_cluster", "unknown"
    raise QualityRatchetError(f"Checkov failed check has unusable resource reference {value!r}")


def parse_checkov(report: Path, _root: Path | None) -> list[Finding]:
    payload = load_json(report)
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), dict):
        raise QualityRatchetError("Checkov JSON must be an object with a results object")
    results = payload["results"]
    if "parsing_errors" not in results or not isinstance(results["parsing_errors"], list):
        raise QualityRatchetError("Checkov report is missing parsing_errors list")
    parsing_errors = results["parsing_errors"]
    if parsing_errors:
        raise QualityRatchetError("Checkov reported parsing errors")
    if "failed_checks" not in results or not isinstance(results["failed_checks"], list):
        raise QualityRatchetError("Checkov report is missing failed_checks list")
    failed_checks = results["failed_checks"]

    findings: dict[str, Finding] = {}
    for entry in failed_checks:
        if not isinstance(entry, dict):
            raise QualityRatchetError("Checkov failed_checks contains a non-object")
        check_id = require_string(entry, "check_id", "Checkov failed check")
        resource = entry.get("resource_address") or entry.get("resource")
        if not isinstance(resource, str) or not resource:
            raise QualityRatchetError("Checkov failed check is missing resource/resource_address")
        api_version, kind, namespace, name = parse_checkov_resource(resource)
        result = entry.get("check_result", {})
        if not isinstance(result, dict):
            raise QualityRatchetError("Checkov failed check has invalid check_result")
        evaluated_keys = result.get("evaluated_keys", [])
        if not isinstance(evaluated_keys, list) or not all(isinstance(key, str) for key in evaluated_keys):
            raise QualityRatchetError("Checkov evaluated_keys must be a list of strings")
        key_hash = digest(json.dumps(sorted(normalized_text(key) for key in evaluated_keys), separators=(",", ":")))
        identity = "|".join(
            (
                "v1",
                "tool=checkov",
                f"check_id={check_id}",
                f"apiVersion={api_version}",
                f"kind={kind}",
                f"namespace={namespace}",
                f"name={name}",
                f"evaluated_keys_hash={key_hash}",
            )
        )
        findings[identity] = Finding(identity=identity, display=f"{check_id} on {kind}/{namespace}/{name}")
    return list(findings.values())


def parse_allowed_exit_codes(value: str) -> set[int]:
    try:
        codes = {int(item) for item in value.split(",") if item.strip()}
    except ValueError as error:
        raise QualityRatchetError(f"Invalid --allowed-exit-codes value {value!r}") from error
    if not codes:
        raise QualityRatchetError("--allowed-exit-codes cannot be empty")
    return codes


def verify_exit_codes(args: argparse.Namespace) -> None:
    allowed = parse_allowed_exit_codes(args.allowed_exit_codes)
    for label, value in (("base", args.base_exit_code), ("head", args.head_exit_code)):
        if value is not None and value not in allowed:
            raise QualityRatchetError(
                f"{args.tool} {label} scan exited {value}, expected one of {sorted(allowed)}"
            )


def summarize(
    tool: str,
    base_findings: Iterable[Finding],
    head_findings: Iterable[Finding],
) -> tuple[str, collections.Counter[str], collections.Counter[str], collections.Counter[str], dict[str, str]]:
    base_list = list(base_findings)
    head_list = list(head_findings)
    if tool == "yamllint":
        base_counter = collections.Counter(finding.identity for finding in base_list)
        head_counter = collections.Counter(finding.identity for finding in head_list)
    else:
        base_counter = collections.Counter({finding.identity: 1 for finding in base_list})
        head_counter = collections.Counter({finding.identity: 1 for finding in head_list})
    display = {finding.identity: finding.display for finding in [*base_list, *head_list]}
    added = head_counter - base_counter
    removed = base_counter - head_counter
    unchanged = base_counter & head_counter
    if added:
        state = "FAIL: NEW DEBT"
    elif not head_counter:
        state = "PASS CLEAN"
    elif removed:
        state = "PASS WITH DEBT REDUCTION"
    else:
        state = "PASS WITH EXISTING DEBT"
    return state, added, removed, unchanged, display


def count(counter: collections.Counter[str]) -> int:
    return sum(counter.values())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_summary(
    path: Path | None,
    tool: str,
    state: str,
    added: collections.Counter[str],
    removed: collections.Counter[str],
    unchanged: collections.Counter[str],
) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(f"## Quality ratchet: {tool}\n\n")
        output.write(f"**{state}**\n\n")
        output.write("| Existing debt | New debt | Debt removed |\n| ---: | ---: | ---: |\n")
        output.write(f"| {count(unchanged)} | {count(added)} | {count(removed)} |\n\n")
        if state == "FAIL: POLICY CHANGES FINDING SET":
            output.write("A proposed policy removed existing findings on trusted content, so it is rejected rather than treated as debt reduction.\n\n")
        elif added:
            output.write("New findings block this PR. Existing findings are retained only while they remain unchanged from the trusted PR base.\n\n")
        elif removed:
            output.write("This PR reduces inherited quality debt without adding new findings.\n\n")
        elif unchanged:
            output.write("This PR does not add quality debt, but inherited findings remain to be remediated.\n\n")
        else:
            output.write("No findings remain for this validator.\n\n")


def emit_annotations(added: collections.Counter[str], display: dict[str, str]) -> None:
    for identity in sorted(added):
        amount = added[identity]
        suffix = f" (x{amount})" if amount > 1 else ""
        print(f"::error title=Quality ratchet new finding::{display.get(identity, identity)}{suffix}")


def main() -> int:
    args = parse_args()
    parsers: dict[str, Callable[[Path, Path | None], list[Finding]]] = {
        "yamllint": parse_yamllint,
        "kubeconform": parse_kubeconform,
        "checkov": parse_checkov,
    }
    try:
        if args.base_sha == args.head_sha:
            raise QualityRatchetError("base and head SHA must differ for a pull-request comparison")
        verify_exit_codes(args)
        parser = parsers[args.tool]
        base_findings = parser(args.base_report, args.base_root)
        head_findings = parser(args.head_report, args.head_root)
        state, added, removed, unchanged, display = summarize(args.tool, base_findings, head_findings)
        policy_suppression = args.reject_removed and bool(removed)
        if policy_suppression and not added:
            state = "FAIL: POLICY CHANGES FINDING SET"
        payload = {
            "version": 1,
            "tool": args.tool,
            "base_sha": args.base_sha,
            "head_sha": args.head_sha,
            "state": state,
            "counts": {
                "base": count(collections.Counter(finding.identity for finding in base_findings)),
                "head": count(collections.Counter(finding.identity for finding in head_findings)),
                "unchanged": count(unchanged),
                "added": count(added),
                "removed": count(removed),
            },
            "added": [{"identity": key, "count": added[key]} for key in sorted(added)],
            "removed": [{"identity": key, "count": removed[key]} for key in sorted(removed)],
        }
        write_json(args.report, payload)
        write_summary(args.github_summary, args.tool, state, added, removed, unchanged)
        if added or policy_suppression:
            if args.github_annotations:
                emit_annotations(added, display)
                if policy_suppression:
                    print("::error title=Quality policy suppressed debt::A policy change removed existing findings.")
            return 1
        return 0
    except QualityRatchetError as error:
        print(f"::error title=Quality ratchet integrity error::{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
