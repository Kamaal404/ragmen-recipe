from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema
import yaml

from blueprint_contract import compute_hash


def validate(path: Path, *, require_approval: bool = False) -> list[str]:
    blueprint = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema = json.loads((Path(__file__).parents[2] / "spec" / "blueprint.schema.json").read_text(encoding="utf-8"))
    errors = [error.message for error in jsonschema.Draft202012Validator(schema).iter_errors(blueprint)]
    if require_approval and not blueprint.get("approval"):
        errors.append("approval is required for runtime execution")
    if blueprint.get("blueprint_version", "").split(".", 1)[0] != "1":
        errors.append("unsupported blueprint version")
    if blueprint.get("blueprint_hash") != compute_hash(blueprint):
        errors.append("blueprint_hash does not match canonical blueprint content")
    communities = blueprint.get("communities", {})
    if any(level >= communities.get("max_levels", 0) for level in communities.get("summarize_levels", [])):
        errors.append("communities.summarize_levels must be within max_levels")
    expected_dimensions = {"all-MiniLM-L6-v2": 384, "bge-small-en-v1.5": 384}.get(
        blueprint.get("embedding", {}).get("model", "").split("/")[-1]
    )
    if expected_dimensions is not None and blueprint["embedding"].get("dimensions") != expected_dimensions:
        errors.append("embedding dimension mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("blueprint", type=Path)
    parser.add_argument("--runtime", action="store_true")
    args = parser.parse_args()
    errors = validate(args.blueprint, require_approval=args.runtime)
    for error in errors:
        print(f"ERROR {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
