"""Lazy YAML knowledge base loader.

Loads scenario YAML files on demand — never at import time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_KB_ROOT = Path(__file__).resolve().parent.parent.parent / "knowledge_base"


def get_kb_root() -> Path:
    return _KB_ROOT


def load_scenario_chunks(scenario: str) -> list[dict[str, Any]]:
    """Load all YAML chunks from a scenario directory."""
    scenario_dir = _KB_ROOT / "scenarios" / scenario
    if not scenario_dir.exists():
        return []
    chunks: list[dict[str, Any]] = []
    for f in sorted(scenario_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if data:
                chunks.append(data)
        except Exception:
            continue
    return chunks


def load_general_prompt() -> str:
    """Load general YAML files and merge into a prompt string."""
    general_dir = _KB_ROOT / "general"
    parts: list[str] = []
    if not general_dir.exists():
        return ""
    for f in sorted(general_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if data and "content" in data:
                parts.append(data["content"])
        except Exception:
            continue
    return "\n\n".join(parts)
