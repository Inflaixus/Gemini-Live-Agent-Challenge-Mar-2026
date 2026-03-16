"""Centralized configuration — loads env vars + YAML config files.

Usage:
    from app.core.config import settings
    settings.voice_name  # "Aoede"
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from .constants import SUPPORTED_RESPONSE_MODALITIES
from .logging import get_logger

logger = get_logger(__name__)

_CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"


def _load_yaml(name: str) -> dict[str, Any]:
    path = _CONFIGS_DIR / name
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes")


def _env_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    return int(val)


def _parse_single_response_modality(raw_value: str | None) -> str:
    """Parse env modality and enforce a single supported value."""
    if not raw_value:
        return "AUDIO"

    parsed_values: list[str] = []
    candidate = raw_value.strip()

    if candidate.startswith("["):
        try:
            as_json = json.loads(candidate)
            if isinstance(as_json, list):
                parsed_values = [
                    str(v).strip().upper() for v in as_json if str(v).strip()
                ]
        except json.JSONDecodeError:
            parsed_values = []

    if not parsed_values:
        parsed_values = [
            part.strip().upper()
            for part in candidate.replace(";", ",").split(",")
            if part.strip()
        ]

    if not parsed_values:
        return "AUDIO"

    if len(parsed_values) > 1:
        logger.warning(
            "LIVE_RESPONSE_MODALITY must be a single value. Received %s; using %s.",
            parsed_values,
            parsed_values[0],
        )

    modality = parsed_values[0]
    if modality not in SUPPORTED_RESPONSE_MODALITIES:
        logger.warning(
            "Unsupported LIVE_RESPONSE_MODALITY=%s. Falling back to AUDIO.",
            modality,
        )
        return "AUDIO"
    return modality


class Settings:
    """Typed access to all configuration values."""

    def __init__(self) -> None:
        runtime = _load_yaml("runtime_config.yaml")
        model_cfg = _load_yaml("model_config.yaml")
        rag_cfg = _load_yaml("rag_config.yaml")

        # --- Agent / Model ---
        self.agent_model: str = os.getenv(
            "AGENT_MODEL",
            model_cfg.get("default_agent_model", "gemini-2.5-flash-native-audio-latest"),
        ).strip()

        # --- Audio / VAD ---
        self.voice_name: str = os.getenv(
            "VOICE_NAME", runtime.get("voice_name", "Aoede")
        )
        self.silence_duration_ms: int = _env_int(
            "SILENCE_DURATION_MS", runtime.get("silence_duration_ms", 140)
        )
        self.prefix_padding_ms: int = _env_int(
            "PREFIX_PADDING_MS", runtime.get("prefix_padding_ms", 10)
        )
        self.audio_activity_peak_threshold: int = _env_int(
            "AUDIO_ACTIVITY_PEAK_THRESHOLD",
            runtime.get("audio_activity_peak_threshold", 380),
        )

        # --- Transcription ---
        self.input_audio_transcription_enabled: bool = _env_bool(
            "INPUT_AUDIO_TRANSCRIPTION_ENABLED",
            runtime.get("input_audio_transcription_enabled", False),
        )
        self.output_audio_transcription_enabled: bool = _env_bool(
            "OUTPUT_AUDIO_TRANSCRIPTION_ENABLED",
            runtime.get("output_audio_transcription_enabled", True),
        )

        # --- Turn coverage ---
        self.turn_coverage_mode: str = os.getenv(
            "TURN_COVERAGE_MODE",
            runtime.get("turn_coverage_mode", "all_input"),
        ).strip().lower()

        # --- Video throttling ---
        self.video_min_forward_interval_ms: int = _env_int(
            "VIDEO_MIN_FORWARD_INTERVAL_MS",
            runtime.get("video_min_forward_interval_ms", 0),
        )
        self.video_suppress_during_audio_ms: int = _env_int(
            "VIDEO_SUPPRESS_DURING_AUDIO_MS",
            runtime.get("video_suppress_during_audio_ms", 0),
        )
        self.video_max_staleness_ms: int = _env_int(
            "VIDEO_MAX_STALENESS_MS",
            runtime.get("video_max_staleness_ms", 0),
        )

        # --- Native audio features ---
        self.enable_proactivity: bool = _env_bool(
            "ENABLE_PROACTIVITY",
            runtime.get("enable_proactivity", False),
        )
        self.enable_affective_dialog: bool = _env_bool(
            "ENABLE_AFFECTIVE_DIALOG",
            runtime.get("enable_affective_dialog", True),
        )

        # --- Response modality ---
        self.response_modality: str = _parse_single_response_modality(
            os.getenv(
                "LIVE_RESPONSE_MODALITY",
                runtime.get("live_response_modality", "AUDIO"),
            )
        )

        # --- Session resumption ---
        self.session_resumption_handle_ttl_seconds: int = _env_int(
            "SESSION_RESUMPTION_HANDLE_TTL_SECONDS",
            runtime.get("session_resumption_handle_ttl_seconds", 7200),
        )

        # --- WebSocket queues ---
        self.audio_queue_maxsize: int = runtime.get("audio_queue_maxsize", 200)
        self.json_queue_maxsize: int = runtime.get("json_queue_maxsize", 200)

        # --- Downstream retry ---
        self.max_downstream_retries: int = runtime.get("max_downstream_retries", 5)

        # --- Context window compression ---
        self.compression_trigger_tokens: int = runtime.get(
            "compression_trigger_tokens", 25000
        )
        self.compression_target_tokens: int = runtime.get(
            "compression_target_tokens", 12500
        )

        # --- Diarization ---
        self.enable_diarization: bool = _env_bool(
            "ENABLE_DIARIZATION",
            model_cfg.get("enable_diarization", False),
        )
        self.diarization_min_speakers: int = _env_int(
            "DIARIZATION_MIN_SPEAKERS",
            model_cfg.get("diarization_min_speakers", 1),
        )
        self.diarization_max_speakers: int = _env_int(
            "DIARIZATION_MAX_SPEAKERS",
            model_cfg.get("diarization_max_speakers", 6),
        )
        self.diarization_languages: list[str] = model_cfg.get(
            "diarization_languages", ["ar-EG", "en-US"]
        )
        self.diarization_model: str = model_cfg.get("diarization_model", "long")

        # --- RAG ---
        self.rag_top_k: int = rag_cfg.get("top_k", 3)
        self.rag_min_score: float = rag_cfg.get("min_score_threshold", 1.0)
        self.rag_exact_phrase_weight: float = rag_cfg.get("exact_phrase_weight", 3.0)
        self.rag_token_overlap_weight: float = rag_cfg.get("token_overlap_weight", 1.8)
        self.rag_topic_weight: float = rag_cfg.get("topic_weight", 0.4)
        self.rag_stopwords: set[str] = set(rag_cfg.get("stopwords", []))

        # --- Scenario ---
        self.default_scenario: str = os.getenv("SCENARIO", "scenario_1")

    def validate_live_audio(self) -> None:
        """Fail fast on known bad model + modality combinations."""
        if self.response_modality != "AUDIO":
            return
        if "native-audio" in self.agent_model:
            return
        from .constants import RECOMMENDED_NATIVE_AUDIO_MODELS

        suggestions = ", ".join(RECOMMENDED_NATIVE_AUDIO_MODELS)
        msg = (
            f"Invalid live audio configuration: response modality is AUDIO but "
            f"AGENT_MODEL='{self.agent_model}' is not a native-audio model. "
            f"Use one of: {suggestions}"
        )
        logger.error(msg)
        raise ValueError(msg)


# Singleton — instantiated once, imported everywhere.
settings = Settings()
