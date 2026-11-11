#!/usr/bin/env python3
"""Select changed image inputs and enforce stable SemVer releases."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def object_id(root, commit, path):
    if commit is None:
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", f"{commit}:{path}"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def version(root, commit, image):
    value = git(root, "show", f"{commit}:images/{image}/VERSION")
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value):
        raise ValueError(f"{image}: VERSION must be a stable SemVer MAJOR.MINOR.PATCH")
    if len(value) > 128:
        raise ValueError(f"{image}: VERSION exceeds Docker's tag length limit")
    return value


def plan(root, base, head):
    for commit in (base, head):
        if commit is not None:
            if not re.fullmatch(r"[0-9a-f]{40}", commit):
                raise ValueError("Expected full Git commit SHAs")
            git(root, "cat-file", "-e", f"{commit}^{{commit}}")
    if object_id(root, head, "images") is None:
        return {"include": []}
    entries = []
    for record in git(root, "ls-tree", f"{head}:images").splitlines():
        metadata, image = record.split("\t", 1)
        if metadata.split()[1] != "tree":
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", image):
            raise ValueError(f"Invalid image directory name: {image}")
        path = f"images/{image}/context"
        context = object_id(root, head, path)
        if not context or not object_id(root, head, f"{path}/Dockerfile"):
            raise ValueError(f"{image}: missing context/Dockerfile")
        current = version(root, head, image)
        previous_context = object_id(root, base, path)
        if previous_context:
            previous = version(root, base, image)
            if (context, current) == (previous_context, previous):
                continue
            if tuple(map(int, current.split("."))) <= tuple(map(int, previous.split("."))):
                raise ValueError(f"{image}: changed image inputs require VERSION greater than {previous}")
        fingerprint = hashlib.sha256(f"linux/amd64\n{context}\n{current}\n".encode()).hexdigest()
        entries.append({"image": image, "version": current, "input_hash": fingerprint})
    return {"include": entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Git repository path")
    parser.add_argument("--base", required=True, help="Base commit SHA; 40 zeros selects the whole catalog")
    parser.add_argument("--head", required=True, help="Commit SHA to build")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON matrix path")
    args = parser.parse_args()
    try:
        result = plan(args.root.resolve(), None if args.base == "0" * 40 else args.base, args.head)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Image build plan failed: {error}\n")
    args.output.write_text(json.dumps(result, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
