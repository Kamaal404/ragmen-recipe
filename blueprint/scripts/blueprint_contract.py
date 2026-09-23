from __future__ import annotations

import hashlib
import json


def canonical_payload(blueprint: dict) -> bytes:
    payload = {key: value for key, value in blueprint.items() if key not in {"blueprint_hash", "approval"}}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_hash(blueprint: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical_payload(blueprint)).hexdigest()
