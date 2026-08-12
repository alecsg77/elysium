#!/usr/bin/env python3
"""Fail closed on destructive changes to reviewed GitOps resources.

The GitHub workflow checks this script and its policy out from the PR base SHA.
The proposed tree is treated only as YAML/Kustomize input: Kustomize exec plugins,
networked functions, and Helm inflation are never enabled by this program.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class GuardError(RuntimeError):
    """A malformed policy or manifest that must fail the PR."""


@dataclass(frozen=True)
class Identity:
    api_version: str
    kind: str
    namespace: str
    name: str

    def display(self) -> str:
        namespace = f"{self.namespace}/" if self.namespace else ""
        return f"{self.api_version} {self.kind} {namespace}{self.name}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path, help="Trusted base checkout")
    parser.add_argument("--head", required=True, type=Path, help="Proposed PR checkout")
    parser.add_argument("--policy", required=True, type=Path, help="Policy from trusted base")
    parser.add_argument("--report", type=Path, help="Optional JSON report path")
    return parser.parse_args()


def read_yaml(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as stream:
            return yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as error:
        raise GuardError(f"Cannot parse YAML {path}: {error}") from error


def documents(rendered: str, label: str) -> dict[Identity, dict[str, Any]]:
    result: dict[Identity, dict[str, Any]] = {}
    try:
        values = yaml.safe_load_all(rendered)
        for document in values:
            if not isinstance(document, dict):
                continue
            api_version = document.get("apiVersion")
            kind = document.get("kind")
            metadata = document.get("metadata")
            if not isinstance(api_version, str) or not isinstance(kind, str) or not isinstance(metadata, dict):
                continue
            name = metadata.get("name")
            namespace = metadata.get("namespace", "")
            if not isinstance(name, str) or not isinstance(namespace, str):
                continue
            identity = Identity(api_version, kind, namespace, name)
            if identity in result:
                raise GuardError(f"{label} renders duplicate identity {identity.display()}")
            result[identity] = document
    except yaml.YAMLError as error:
        raise GuardError(f"Cannot parse rendered YAML for {label}: {error}") from error
    return result


def raw_documents(tree: Path, relative_path: str) -> dict[Identity, dict[str, Any]]:
    """Load a policy-selected YAML file without evaluating Kustomize."""
    path = tree / relative_path
    if not path.is_file():
        raise GuardError(f"Required raw policy target is missing: {path}")
    try:
        return documents(path.read_text(encoding="utf-8"), relative_path)
    except OSError as error:
        raise GuardError(f"Cannot read raw policy target {path}: {error}") from error


def kustomization_file(directory: Path) -> Path | None:
    """Return the local Kustomization file in a directory, when present."""
    return next(
        (directory / name for name in ("kustomization.yaml", "kustomization.yml", "Kustomization") if (directory / name).is_file()),
        None,
    )


def is_remote_kustomize_reference(value: str) -> bool:
    """Return whether a Kustomize resource/component value resolves remotely."""
    return "://" in value or value.startswith(("git::", "github.com/", "git@", "ssh://"))


def assert_no_direct_remote_kustomize_bases(target: Path) -> None:
    """Reject remote declarations in one local Kustomization manifest."""
    manifest_path = kustomization_file(target)
    if manifest_path is None:
        raise GuardError(f"Guard render target has no local Kustomization: {target}")
    manifest = read_yaml(manifest_path)
    if not isinstance(manifest, dict):
        raise GuardError(f"Guard render target is not a YAML mapping: {manifest_path}")
    for field in ("resources", "components", "crds"):
        values = manifest.get(field, [])
        if values is None:
            continue
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise GuardError(f"Guard render target has invalid {field}: {manifest_path}")
        for value in values:
            if is_remote_kustomize_reference(value):
                raise GuardError(f"Guard render target declares a remote {field} entry in {manifest_path}: {value}")


def assert_no_remote_kustomize_bases(tree: Path, target: Path) -> None:
    """Reject remote bases anywhere reachable from a guard render target.

    Kustomize resolves nested local bases recursively. Checking only the root
    Kustomization would allow a PR to add a remote base in a child directory, so
    walk each local resource/component/CRD Kustomization before invoking the
    renderer. Traversal is confined to the checkout to prevent path escapes.
    """
    root = tree.resolve()
    pending = [target.resolve()]
    visited: set[Path] = set()

    while pending:
        directory = pending.pop()
        if directory in visited:
            continue
        visited.add(directory)
        try:
            directory.relative_to(root)
        except ValueError as error:
            raise GuardError(f"Guard render target escapes the checkout: {directory}") from error

        manifest_path = kustomization_file(directory)
        if manifest_path is None:
            raise GuardError(f"Guard render target has no local Kustomization: {directory}")
        manifest = read_yaml(manifest_path)
        if not isinstance(manifest, dict):
            raise GuardError(f"Guard render target is not a YAML mapping: {manifest_path}")

        for field in ("resources", "components", "crds"):
            values = manifest.get(field, [])
            if values is None:
                continue
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise GuardError(f"Guard render target has invalid {field}: {manifest_path}")
            for value in values:
                if is_remote_kustomize_reference(value):
                    raise GuardError(
                        f"Guard render target declares a remote {field} entry in {manifest_path}: {value}"
                    )
                child = (directory / value).resolve()
                try:
                    child.relative_to(root)
                except ValueError as error:
                    raise GuardError(
                        f"Guard render target declares a {field} entry outside the checkout in {manifest_path}: {value}"
                    ) from error
                if child.is_dir() and kustomization_file(child) is not None:
                    pending.append(child)


def render(tree: Path, relative_target: str) -> dict[Identity, dict[str, Any]]:
    target = tree / relative_target
    if not target.is_dir():
        raise GuardError(f"Required render target is missing: {target}")
    assert_no_remote_kustomize_bases(tree, target)

    environment = os.environ.copy()
    # Kustomize plugins/functions are disabled unless explicitly enabled. Set the
    # plugin home to a non-existent directory as an additional guardrail.
    environment["KUSTOMIZE_PLUGIN_HOME"] = str(tree / ".disabled-kustomize-plugins")
    completed = subprocess.run(
        ["kustomize", "build", str(target)],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise GuardError(f"kustomize build failed for {relative_target}: {detail}")
    return documents(completed.stdout, relative_target)


def identity_from_policy(entry: dict[str, Any]) -> Identity:
    required = ("apiVersion", "kind", "name")
    missing = [key for key in required if not isinstance(entry.get(key), str)]
    if missing:
        raise GuardError(f"Critical-resource policy entry is missing {', '.join(missing)}")
    namespace = entry.get("namespace", "")
    if not isinstance(namespace, str):
        raise GuardError("Critical-resource policy namespace must be a string")
    return Identity(entry["apiVersion"], entry["kind"], namespace, entry["name"])


def value_at(document: dict[str, Any], dotted_path: str) -> Any:
    """Resolve mapping fields while supporting Kubernetes keys containing dots."""
    value: Any = document
    parts = dotted_path.split(".")
    for index, part in enumerate(parts):
        if not isinstance(value, dict):
            return None
        if part in value:
            value = value[part]
            continue
        # Annotation and label keys commonly contain dots and slashes. If the next
        # component is not a mapping key, consume the remaining path as one key.
        remaining = ".".join(parts[index:])
        if remaining in value:
            return value[remaining]
        return None
    return value


def validate_root_composition(tree: Path, policy: dict[str, Any], side: str) -> list[str]:
    root = policy.get("root_composition")
    if not isinstance(root, dict):
        raise GuardError("Policy root_composition must be an object")
    relative_path = root.get("path")
    expected_resources = root.get("resources")
    if not isinstance(relative_path, str) or not isinstance(expected_resources, list) or not all(
        isinstance(item, str) for item in expected_resources
    ):
        raise GuardError("Policy root_composition must contain path and string resources")

    manifest_path = tree / relative_path
    if not manifest_path.is_file():
        return [f"{side}: required root composition file is missing: {relative_path}"]
    manifest = read_yaml(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("apiVersion") != "kustomize.config.k8s.io/v1beta1" or manifest.get(
        "kind"
    ) != "Kustomization":
        return [f"{side}: {relative_path} is not the expected local Kustomization"]
    actual_resources = manifest.get("resources")
    if actual_resources != expected_resources:
        return [
            f"{side}: {relative_path} must contain exactly {expected_resources}; found {actual_resources!r}"
        ]
    return []


def intent_allows(
    base: Path, head: Path, policy: dict[str, Any], resource_id: str, operation: str
) -> tuple[bool, str]:
    """Allow one R2 operation only after a consumed prior intent on main.

    The first PR adds a resource-specific intent containing backup and rollback
    evidence. The later destructive PR must remove that intent as well as make
    the R2 change, preventing an old intent from authorizing a future operation.
    """
    intent_directory = policy.get("intent_directory")
    if not isinstance(intent_directory, str):
        raise GuardError("Policy intent_directory must be a string")
    filename = resource_id.replace("/", "__") + ".yaml"
    base_path = base / intent_directory / filename
    head_path = head / intent_directory / filename
    if not base_path.is_file():
        return False, f"missing prior intent {intent_directory}/{filename}"
    if head_path.exists():
        return False, f"prior intent {intent_directory}/{filename} must be consumed in the R2 PR"
    intent = read_yaml(base_path)
    if not isinstance(intent, dict):
        return False, f"invalid prior intent {base_path.relative_to(base)}"
    if intent.get("resource") != resource_id:
        return False, f"prior intent {base_path.relative_to(base)} names a different resource"
    if intent.get("operation") != operation:
        return (
            False,
            f"prior intent {base_path.relative_to(base)} has operation {intent.get('operation')!r}, expected {operation!r}",
        )
    for field in ("backup", "rollback"):
        if not isinstance(intent.get(field), str) or not intent[field].strip():
            return False, f"prior intent {base_path.relative_to(base)} has no {field} evidence"
    return True, f"consumed prior intent {base_path.relative_to(base)} permits {operation}"


def validate_intent_files(
    base: Path, head: Path, policy: dict[str, Any], resource_ids: set[str]
) -> tuple[list[str], set[str]]:
    """Validate newly declared R2 intents and make existing intents immutable.

    A preparation PR is useful only if its evidence is valid before it reaches
    main. Once present on main, an intent may be consumed by its matching R2 PR,
    but cannot be edited to authorize a different operation.
    """
    intent_directory = policy.get("intent_directory")
    if not isinstance(intent_directory, str):
        raise GuardError("Policy intent_directory must be a string")

    base_directory = base / intent_directory
    head_directory = head / intent_directory
    base_files = {path.name: path for path in base_directory.glob("*.yaml")} if base_directory.is_dir() else {}
    head_files = {path.name: path for path in head_directory.glob("*.yaml")} if head_directory.is_dir() else {}
    errors: list[str] = []
    removed_resources: set[str] = set()

    def validate(path: Path, side: str) -> str | None:
        document = read_yaml(path)
        if not isinstance(document, dict):
            errors.append(f"{side}: R2 intent {path.name} is not a YAML mapping")
            return None
        resource = document.get("resource")
        operation = document.get("operation")
        if not isinstance(resource, str) or resource not in resource_ids:
            errors.append(f"{side}: R2 intent {path.name} names an unknown critical resource")
            return None
        expected_name = resource.replace("/", "__") + ".yaml"
        if path.name != expected_name:
            errors.append(f"{side}: R2 intent {path.name} must be named {expected_name}")
        if operation not in {"remove", "change"}:
            errors.append(f"{side}: R2 intent {path.name} must declare operation remove or change")
        for field in ("backup", "rollback"):
            if not isinstance(document.get(field), str) or not document[field].strip():
                errors.append(f"{side}: R2 intent {path.name} has no {field} evidence")
        return resource

    for name, path in head_files.items():
        resource = validate(path, "head")
        if name in base_files and base_files[name].read_bytes() != path.read_bytes():
            errors.append(f"head: existing R2 intent must not be modified: {intent_directory}/{name}")
        if resource is not None and name not in base_files:
            # Validation above records a new, machine-readable preparation intent.
            continue

    for name, path in base_files.items():
        resource = validate(path, "base")
        if name not in head_files and resource is not None:
            removed_resources.add(resource)

    return errors, removed_resources


def matching_files(tree: Path, pattern: str) -> set[Path]:
    """Return regular files selected by a small, policy-safe glob subset."""
    if pattern.endswith("/**"):
        root = tree / pattern[:-3]
        if not root.exists():
            return set()
        return {path for path in root.rglob("*") if path.is_file()}
    path = tree / pattern
    return {path} if path.is_file() else set()


def changed_tier0_paths(base: Path, head: Path, policy: dict[str, Any]) -> list[str]:
    patterns = policy.get("tier0_paths", [])
    if not isinstance(patterns, list) or not all(isinstance(pattern, str) for pattern in patterns):
        raise GuardError("Policy tier0_paths must contain strings")

    changed: set[str] = set()
    for pattern in patterns:
        base_files = matching_files(base, pattern)
        head_files = matching_files(head, pattern)
        relative_files = {
            path.relative_to(base) for path in base_files
        } | {
            path.relative_to(head) for path in head_files
        }
        for relative_path in relative_files:
            base_path = base / relative_path
            head_path = head / relative_path
            base_content = base_path.read_bytes() if base_path.is_file() else None
            head_content = head_path.read_bytes() if head_path.is_file() else None
            if base_content != head_content:
                changed.add(relative_path.as_posix())
    return sorted(changed)


def names_from_depends_on(document: dict[str, Any], label: str) -> list[str]:
    spec = document.get("spec")
    if not isinstance(spec, dict):
        raise GuardError(f"{label} has no spec mapping")
    depends_on = spec.get("dependsOn", [])
    if depends_on is None:
        depends_on = []
    if not isinstance(depends_on, list):
        raise GuardError(f"{label} spec.dependsOn must be a list")
    names: list[str] = []
    for dependency in depends_on:
        if not isinstance(dependency, dict) or not isinstance(dependency.get("name"), str):
            raise GuardError(f"{label} has an invalid spec.dependsOn entry")
        names.append(dependency["name"])
    return names


def validate_bootstrap_semantics(
    resources: dict[Identity, dict[str, Any]], policy: dict[str, Any], side: str
) -> list[str]:
    """Validate the fixed Flux dependency boundary and substitution inputs."""
    expected_dependencies = policy.get("bootstrap_dependencies")
    if not isinstance(expected_dependencies, dict) or not all(
        isinstance(name, str) and isinstance(dependencies, list) and all(isinstance(dep, str) for dep in dependencies)
        for name, dependencies in expected_dependencies.items()
    ):
        raise GuardError("Policy bootstrap_dependencies must map names to string lists")

    errors: list[str] = []
    bootstrap: dict[str, dict[str, Any]] = {}
    for identity, document in resources.items():
        if (
            identity.api_version == "kustomize.toolkit.fluxcd.io/v1"
            and identity.kind == "Kustomization"
            and identity.namespace == "flux-system"
            and identity.name in expected_dependencies
        ):
            bootstrap[identity.name] = document

    for name, expected in expected_dependencies.items():
        document = bootstrap.get(name)
        if document is None:
            errors.append(f"{side}: required bootstrap Kustomization is absent: {name}")
            continue
        actual = names_from_depends_on(document, f"{side}: bootstrap/{name}")
        if actual != expected:
            errors.append(
                f"{side}: bootstrap/{name} spec.dependsOn must be exactly {expected}; found {actual}"
            )

        spec = document.get("spec")
        assert isinstance(spec, dict)  # validated by names_from_depends_on
        source_ref = spec.get("sourceRef")
        if not isinstance(source_ref, dict) or not isinstance(source_ref.get("kind"), str) or not isinstance(
            source_ref.get("name"), str
        ):
            errors.append(f"{side}: bootstrap/{name} has an invalid spec.sourceRef")
        path = spec.get("path")
        if not isinstance(path, str) or not path.startswith("./"):
            errors.append(f"{side}: bootstrap/{name} must declare a repository-relative spec.path")

        post_build = spec.get("postBuild")
        if not isinstance(post_build, dict):
            errors.append(f"{side}: bootstrap/{name} has no spec.postBuild mapping")
            continue
        substitutions = post_build.get("substituteFrom")
        if not isinstance(substitutions, list) or not substitutions:
            errors.append(f"{side}: bootstrap/{name} has no spec.postBuild.substituteFrom entries")
            continue
        for source in substitutions:
            if not isinstance(source, dict) or not isinstance(source.get("kind"), str) or not isinstance(
                source.get("name"), str
            ):
                errors.append(f"{side}: bootstrap/{name} has an invalid substituteFrom entry")
                continue
            source_kind = source["kind"]
            source_name = source["name"]
            direct = Identity("v1", source_kind, "flux-system", source_name)
            sealed = Identity("bitnami.com/v1alpha1", "SealedSecret", "flux-system", source_name)
            if direct not in resources and not (source_kind == "Secret" and sealed in resources):
                errors.append(
                    f"{side}: bootstrap/{name} substituteFrom {source_kind}/{source_name} is not provided by root composition"
                )
    return errors


def validate_bootstrap_paths(
    tree: Path, resources: dict[Identity, dict[str, Any]], policy: dict[str, Any], side: str
) -> list[str]:
    """Ensure every Flux child path exists without evaluating its full tree.

    The trusted guard renders its explicit local leaf targets. It intentionally
    does not build aggregate child paths here: some catalog paths legitimately
    contain remote bases, which would turn a trusted-base comparison into a
    network fetch of PR-controlled configuration. The GitOps validator performs
    the broader render separately on an ephemeral runner without credentials.
    """
    expected_dependencies = policy.get("bootstrap_dependencies")
    assert isinstance(expected_dependencies, dict)
    errors: list[str] = []
    for name in expected_dependencies:
        identity = Identity("kustomize.toolkit.fluxcd.io/v1", "Kustomization", "flux-system", name)
        document = resources.get(identity)
        if document is None:
            continue
        spec = document.get("spec")
        if not isinstance(spec, dict) or not isinstance(spec.get("path"), str):
            continue
        relative_path = spec["path"].removeprefix("./")
        target = tree / relative_path
        if not target.is_dir():
            errors.append(f"{side}: bootstrap/{name} spec.path is missing: {relative_path}")
            continue
        try:
            # Bootstrap aggregates can contain non-critical legacy remote bases.
            # The trusted guard renders declared local leaf targets separately and
            # never follows a remote entry from a PR-controlled child path here.
            assert_no_direct_remote_kustomize_bases(target)
        except GuardError as error:
            errors.append(f"{side}: bootstrap/{name} path validation failed: {error}")
    return errors


def safe_hardening_allows(
    policy: dict[str, Any], event: dict[str, Any], base_document: dict[str, Any], head_document: dict[str, Any]
) -> tuple[bool, str]:
    """Allow only exact non-destructive Flux protection transitions."""
    safe_hardening = policy.get("safe_hardening")
    if not isinstance(safe_hardening, dict):
        raise GuardError("Policy safe_hardening must be a mapping")

    field = event.get("field")
    if field == "spec.deletionPolicy":
        desired = safe_hardening.get("deletion_policy")
        if value_at(base_document, field) is None and value_at(head_document, field) == desired:
            return True, f"safe hardening sets {field} to {desired!r}"
        return False, f"{field} is not the allowed safe-hardening transition"

    if field == "metadata.annotations":
        desired = safe_hardening.get("prune_annotation")
        if not isinstance(desired, str):
            raise GuardError("Policy safe_hardening.prune_annotation must be a string")
        base_annotations = value_at(base_document, field)
        head_annotations = value_at(head_document, field)
        if base_annotations is None:
            base_annotations = {}
        if not isinstance(base_annotations, dict) or not isinstance(head_annotations, dict):
            return False, "prune hardening must preserve the annotations mapping"
        prune_annotation = "kustomize.toolkit.fluxcd.io/prune"
        expected_head = {**base_annotations, prune_annotation: desired}
        if prune_annotation not in base_annotations and head_annotations == expected_head:
            return True, f"safe hardening adds {prune_annotation}: {desired}"
        return False, "metadata.annotations is not the allowed prune hardening transition"

    return False, "not a safe-hardening field"


def preparation_allows_deprotection(
    base: Path, head: Path, policy: dict[str, Any], event: dict[str, Any], base_document: dict[str, Any], head_document: dict[str, Any]
) -> tuple[bool, str]:
    """Allow PR 1 to add an intent and remove only the Flux prune opt-out.

    The second PR consumes that intent while removing the protected resource. This
    is the only critical-field change permitted in the preparation PR.
    """
    if event.get("operation") != "change" or event.get("field") != "metadata.annotations":
        return False, "not a prune deprotection event"
    resource_id = event.get("resource")
    if not isinstance(resource_id, str):
        return False, "invalid critical resource id"

    base_annotations = value_at(base_document, "metadata.annotations")
    head_annotations = value_at(head_document, "metadata.annotations")
    if not isinstance(base_annotations, dict) or head_annotations not in (None, {}) and not isinstance(head_annotations, dict):
        return False, "prune deprotection must preserve the annotations mapping"
    if head_annotations is None:
        head_annotations = {}
    prune_annotation = "kustomize.toolkit.fluxcd.io/prune"
    if base_annotations.get(prune_annotation) != "disabled" or prune_annotation in head_annotations:
        return False, "only removal of the prune: disabled annotation is permitted in a preparation PR"
    expected_head = {key: value for key, value in base_annotations.items() if key != prune_annotation}
    if head_annotations != expected_head:
        return False, "preparation PR changed annotations other than the prune opt-out"

    intent_directory = policy.get("intent_directory")
    if not isinstance(intent_directory, str):
        raise GuardError("Policy intent_directory must be a string")
    filename = resource_id.replace("/", "__") + ".yaml"
    base_path = base / intent_directory / filename
    head_path = head / intent_directory / filename
    if base_path.exists():
        return False, f"preparation intent {intent_directory}/{filename} must be newly added"
    if not head_path.is_file():
        return False, f"missing preparation intent {intent_directory}/{filename}"
    intent = read_yaml(head_path)
    if not isinstance(intent, dict):
        return False, f"invalid preparation intent {head_path.relative_to(head)}"
    if intent.get("resource") != resource_id or intent.get("operation") != "remove":
        return False, f"preparation intent {head_path.relative_to(head)} must declare {resource_id} remove"
    for field in ("backup", "rollback"):
        if not isinstance(intent.get(field), str) or not intent[field].strip():
            return False, f"preparation intent {head_path.relative_to(head)} has no {field} evidence"
    return True, f"new preparation intent {head_path.relative_to(head)} permits prune deprotection"


def main() -> int:
    args = parse_args()
    base = args.base.resolve()
    head = args.head.resolve()
    policy_path = args.policy.resolve()
    report: dict[str, Any] = {"r1": [], "r2": [], "errors": [], "permitted_r2": []}

    try:
        policy = read_yaml(policy_path)
        if not isinstance(policy, dict) or policy.get("version") != 1:
            raise GuardError("Critical-resource policy must be a version: 1 mapping")

        for side, tree in (("base", base), ("head", head)):
            report["errors"].extend(validate_root_composition(tree, policy, side))

        for relative_path in policy.get("non_removable_files", []):
            if not isinstance(relative_path, str):
                raise GuardError("Policy non_removable_files must contain strings")
            if not (head / relative_path).is_file():
                report["errors"].append(f"head: protected file is missing or renamed: {relative_path}")

        # A missing root composition file would make every later render fail with
        # a generic Kustomize error. Surface the actual safety violation first.
        if report["errors"]:
            print("::error::Critical GitOps guard errors:")
            for error in report["errors"]:
                print(f"  - {error}")
            if args.report:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return 1

        targets = policy.get("render_targets")
        raw_targets = policy.get("raw_file_targets", {})
        entries = policy.get("resources")
        if not isinstance(targets, dict) or not isinstance(raw_targets, dict) or not isinstance(entries, list):
            raise GuardError("Policy must contain render_targets, raw_file_targets, and resources")

        resource_ids = {
            entry.get("id") for entry in entries if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        intent_errors, consumed_intent_resources = validate_intent_files(base, head, policy, resource_ids)
        report["errors"].extend(intent_errors)

        rendered: dict[str, tuple[dict[Identity, dict[str, Any]], dict[Identity, dict[str, Any]]]] = {}
        r2_records: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]] = []
        needed_targets = {entry.get("target") for entry in entries if isinstance(entry, dict)}
        for target_name in needed_targets:
            if not isinstance(target_name, str):
                raise GuardError(f"Invalid target {target_name!r} in policy")
            if isinstance(targets.get(target_name), str):
                relative_target = targets[target_name]
                rendered[target_name] = (render(base, relative_target), render(head, relative_target))
            elif isinstance(raw_targets.get(target_name), str):
                relative_target = raw_targets[target_name]
                rendered[target_name] = (raw_documents(base, relative_target), raw_documents(head, relative_target))
            else:
                raise GuardError(f"Unknown render target {target_name!r} in policy")

        bootstrap_base, bootstrap_head = rendered.get("bootstrap", ({}, {}))
        report["errors"].extend(validate_bootstrap_semantics(bootstrap_base, policy, "base"))
        report["errors"].extend(validate_bootstrap_semantics(bootstrap_head, policy, "head"))
        report["errors"].extend(validate_bootstrap_paths(base, bootstrap_base, policy, "base"))
        report["errors"].extend(validate_bootstrap_paths(head, bootstrap_head, policy, "head"))

        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
                raise GuardError("Every policy resource needs a string id")
            resource_id = entry["id"]
            identity = identity_from_policy(entry)
            target_name = entry.get("target")
            base_resources, head_resources = rendered[target_name]
            base_document = base_resources.get(identity)
            head_document = head_resources.get(identity)
            if base_document is None:
                raise GuardError(f"Policy resource {resource_id} is absent from trusted base render: {identity.display()}")

            if head_document is None:
                event = {"resource": resource_id, "operation": "remove", "detail": identity.display()}
                report["r2"].append(event)
                r2_records.append((event, base_document, None))
                continue

            for level, field_name in (("r1", "r1_fields"), ("r2", "r2_fields")):
                fields = entry.get(field_name, [])
                if not isinstance(fields, list) or not all(isinstance(field, str) for field in fields):
                    raise GuardError(f"Policy {resource_id} has invalid {field_name}")
                for field in fields:
                    if value_at(base_document, field) != value_at(head_document, field):
                        event = {
                            "resource": resource_id,
                            "operation": "change",
                            "field": field,
                            "detail": identity.display(),
                        }
                        report[level].append(event)
                        if level == "r2":
                            r2_records.append((event, base_document, head_document))

        tier0_changes = changed_tier0_paths(base, head, policy)
        if tier0_changes:
            report["tier0"] = tier0_changes
            if report["r1"] or report["r2"] or report["errors"]:
                report["errors"].append(
                    "Tier 0 enforcement paths changed together with a critical-resource change: "
                    + ", ".join(tier0_changes)
                )

        if consumed_intent_resources:
            r2_resources = {event["resource"] for event in report["r2"]}
            for resource_id in sorted(consumed_intent_resources - r2_resources):
                report["errors"].append(
                    f"head: R2 intent for {resource_id} was consumed without a matching R2 operation"
                )

        unapproved: list[dict[str, Any]] = []
        for event, base_document, head_document in r2_records:
            if event["operation"] == "remove":
                allowed, detail = intent_allows(base, head, policy, event["resource"], event["operation"])
            else:
                if head_document is None:
                    raise GuardError("R2 change event has no proposed resource document")
                allowed, detail = safe_hardening_allows(policy, event, base_document, head_document)
                if not allowed and event.get("field") == "metadata.annotations":
                    allowed, detail = preparation_allows_deprotection(
                        base, head, policy, event, base_document, head_document
                    )
                elif not allowed:
                    allowed, detail = intent_allows(base, head, policy, event["resource"], event["operation"])
            if allowed:
                event["intent"] = detail
                report["permitted_r2"].append(event)
            else:
                event["intent"] = detail
                unapproved.append(event)

        if report["r1"]:
            print("::warning::Critical R1 changes detected; automatic semantic checks passed:")
            for event in report["r1"]:
                print(f"  - {event['resource']} {event['field']} ({event['detail']})")
        if report["permitted_r2"]:
            print("Critical R2 changes permitted by a prior branch-bound intent:")
            for event in report["permitted_r2"]:
                print(f"  - {event['resource']} {event['operation']}: {event['intent']}")
        if report["errors"]:
            print("::error::Critical GitOps guard errors:")
            for error in report["errors"]:
                print(f"  - {error}")
        if unapproved:
            print("::error::Unapproved destructive R2 changes:")
            for event in unapproved:
                print(f"  - {event['resource']} {event['operation']} ({event['detail']}): {event['intent']}")

        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 1 if report["errors"] or unapproved else 0
    except GuardError as error:
        print(f"::error::{error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
