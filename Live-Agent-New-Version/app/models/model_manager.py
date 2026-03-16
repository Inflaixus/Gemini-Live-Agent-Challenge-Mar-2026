"""Model manager — resolves modality enums and validates model settings."""

from __future__ import annotations

from google.genai import types


def resolve_response_modality(modality: str):
    """Return enum modality when available, otherwise fallback to string."""
    try:
        enum_cls = getattr(types, "Modality", None)
        if enum_cls is not None and hasattr(enum_cls, modality):
            return getattr(enum_cls, modality)
    except Exception:
        pass
    return modality
