"""Agent service — wraps ADK Runner and run_config building.

Initialised lazily via init(). No import-time side effects.
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner, RunConfig
from google.genai import types

from app.core.config import settings
from app.core.constants import APP_NAME
from app.core.logging import get_logger
from app.models.model_manager import resolve_response_modality
from app.services.session_service import get_adk_session_service

logger = get_logger(__name__)

_runner: Runner | None = None
_agent: Agent | None = None


def init(agent: Agent) -> None:
    """Initialise the agent service with a fully-constructed Agent."""
    global _runner, _agent
    _agent = agent
    _runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=get_adk_session_service(),
    )
    logger.info("AgentService initialised with model=%s", settings.agent_model)


def get_runner() -> Runner:
    if _runner is None:
        raise RuntimeError("AgentService not initialised — call init() first")
    return _runner


def build_run_config(resume_handle: str | None = None, voice_name: str | None = None) -> RunConfig:
    """Build a RunConfig from current settings."""
    session_resumption_config = (
        types.SessionResumptionConfig(handle=resume_handle)
        if resume_handle
        else types.SessionResumptionConfig()
    )

    if settings.turn_coverage_mode == "all_input":
        turn_coverage = types.TurnCoverage.TURN_INCLUDES_ALL_INPUT
    else:
        turn_coverage = types.TurnCoverage.TURN_INCLUDES_ONLY_ACTIVITY

    # Use custom voice_name if provided, otherwise fall back to settings
    effective_voice_name = voice_name if voice_name else settings.voice_name

    run_config_kwargs = {
        "response_modalities": [resolve_response_modality(settings.response_modality)],
        "streaming_mode": StreamingMode.BIDI,
        "session_resumption": session_resumption_config,
        "context_window_compression": types.ContextWindowCompressionConfig(
            trigger_tokens=settings.compression_trigger_tokens,
            sliding_window=types.SlidingWindow(
                target_tokens=settings.compression_target_tokens,
            ),
        ),
        "realtime_input_config": types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                prefix_padding_ms=settings.prefix_padding_ms,
                silence_duration_ms=settings.silence_duration_ms,
            ),
            activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
            turn_coverage=turn_coverage,
        ),
        "speech_config": types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=effective_voice_name,
                )
            )
        ),
    }

    if settings.output_audio_transcription_enabled:
        run_config_kwargs["output_audio_transcription"] = types.AudioTranscriptionConfig()
    if settings.input_audio_transcription_enabled:
        run_config_kwargs["input_audio_transcription"] = types.AudioTranscriptionConfig()

    if "native-audio" in settings.agent_model:
        if settings.enable_proactivity:
            run_config_kwargs["proactivity"] = types.ProactivityConfig(
                proactive_audio=True
            )
        if settings.enable_affective_dialog:
            run_config_kwargs["enable_affective_dialog"] = True

    return RunConfig(**run_config_kwargs)
