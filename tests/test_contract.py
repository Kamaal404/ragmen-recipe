from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parents[1] / "blueprint" / "scripts"))
from blueprint_contract import compute_hash
from validate_blueprint import validate


ROOT = Path(__file__).parents[1]
VALID_VECTORS = sorted((ROOT / "spec/test-vectors/valid").glob("*.yaml"))
INVALID_VECTORS = sorted((ROOT / "spec/test-vectors/invalid").glob("*.yaml"))


def blueprint(**overrides: object) -> dict:
    value = {"blueprint_version": "1.0.0", "name": "sample", "structure": {}, "ontology": {"node_types": [], "relationship_types": [], "patterns": [], "closed": True}, "embedding": {"model": "test", "dimensions": 128, "targets": [{}]}, "workload": {}, "communities": {"algorithm": "leiden", "max_levels": 2, "summarize_levels": [0, 1], "included_node_types": [], "included_relationship_types": [], "summary_prompt": "Summarize."}}
    value.update(overrides)
    value["blueprint_hash"] = compute_hash(value)
    return value


def write(tmp_path: Path, value: dict) -> Path:
    path = tmp_path / "bp.yaml"
    path.write_text(yaml.safe_dump(value), encoding="utf-8")
    return path


def test_canonical_hash_excludes_hash_and_approval() -> None:
    value = blueprint()
    digest = value["blueprint_hash"]
    value["approval"] = {"approved_by": "user", "approved_at": "2026-09-23T00:00:00Z"}
    assert compute_hash(value) == digest


@pytest.mark.parametrize("field,value", [("algorithm", "label_propagation"), ("max_levels", 0), ("summarize_levels", [2])])
def test_community_rules(tmp_path: Path, field: str, value: object) -> None:
    communities = blueprint()["communities"]
    communities[field] = value
    assert validate(write(tmp_path, blueprint(communities=communities)) )


def test_runtime_requires_approval(tmp_path: Path) -> None:
    assert any("approval" in error for error in validate(write(tmp_path, blueprint()), require_approval=True))


def test_valid_vectors_have_valid_contracts() -> None:
    assert VALID_VECTORS


@pytest.mark.parametrize("path", VALID_VECTORS, ids=lambda path: path.stem)
def test_valid_vector(path: Path) -> None:
    assert validate(path) == []


@pytest.mark.parametrize("path", INVALID_VECTORS, ids=lambda path: path.stem)
def test_invalid_vector(path: Path) -> None:
    assert validate(path, require_approval=True)
