from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml
from typing import Any


@dataclass
class KB:
    policy_text: str
    case_chunks: list[dict]
    global_dental_chunks: list[dict]
    nudges: list[dict]
    emotional_chunk: dict | None
    opening_chunk: dict | None


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _chunk_is_indexable(chunk: dict) -> bool:
    """
    Only embed/index chunks that are "patient knowledge" content.
    Exclude controller-only nudges from embedding.
    """
    if chunk.get("audience") == "controller_only":
        return False
    if chunk.get("topic") == "nudges":
        return False
    # policy should not be here anyway, but keep defensive
    if chunk.get("topic") == "policy_scope_and_disclosure":
        return False
    # Opening statement should not be indexed (only used once at start)
    if chunk.get("visibility_rule") == "volunteer_opening_only":
        return False
    return True


def load_kb(kb_root: Path, case_id: str, enable_global_dental: bool = True) -> KB:
    # 1) Global policy (NOT embedded)
    policy_obj = _load_yaml(kb_root / "global_policy.yaml")
    policy_text = policy_obj.get("content", "").strip()

    # 2) Active case chunks
    case_dir = kb_root / "cases" / case_id
    if not case_dir.exists():
        raise FileNotFoundError(f"Case directory not found: {case_dir}")

    raw_case_chunks = []
    for p in sorted(case_dir.glob("*.yaml")):
        raw_case_chunks.append(_load_yaml(p))

    # Pull out nudges, emotional profile, opening
    nudges: list[dict] = []
    emotional_chunk = None
    opening_chunk = None

    indexable_case_chunks: list[dict] = []
    for ch in raw_case_chunks:
        if ch.get("topic") == "nudges" or ch.get("audience") == "controller_only":
            # nudges file structure: {content: [ {id, trigger, patient_prompt, fire_once}, ... ]}
            content = ch.get("content", [])
            if isinstance(content, list):
                nudges.extend(content)
            continue

        if ch.get("topic") == "emotional_profile":
            emotional_chunk = ch  # always injected later

        if ch.get("visibility_rule") == "volunteer_opening_only":
            opening_chunk = ch

        if _chunk_is_indexable(ch):
            indexable_case_chunks.append(ch)

    # 3) Optional global dental KB (embedded, used as fallback)
    global_dental_chunks: list[dict] = []
    if enable_global_dental:
        gd_path = kb_root / "global_dental.yaml"
        if gd_path.exists():
            gd = _load_yaml(gd_path)
            # allow single chunk or list of chunks
            if isinstance(gd, list):
                global_dental_chunks = gd
            else:
                global_dental_chunks = [gd]

    return KB(
        policy_text=policy_text,
        case_chunks=indexable_case_chunks,
        global_dental_chunks=global_dental_chunks,
        nudges=nudges,
        emotional_chunk=emotional_chunk,
        opening_chunk=opening_chunk,
    )