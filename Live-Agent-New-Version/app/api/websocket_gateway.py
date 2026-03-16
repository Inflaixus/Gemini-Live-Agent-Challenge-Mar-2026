"""WebSocket gateway — handles the live audio session lifecycle.

Replaces the monolithic websocket_endpoint from the original app.py.
Uses a session-scoped class to eliminate nested closures.
"""

from __future__ import annotations

import array
import asyncio
import base64
import json
import re
import time
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from google.adk.agents import LiveRequestQueue
from google.genai import types

from app.core.config import settings
from app.core.constants import LEAKY_MODEL_PATTERNS, VISUAL_UNCLEAR_PATTERNS
from app.core.logging import get_logger
from app.api.protocol import (
    parse_client_message,
    TextInput,
    ImageInput,
    VideoFrame,
    PdfInput,
)
from app.services import agent_service, session_service
from app.services.diarization_service import get_diarizer

logger = get_logger(__name__)
router = APIRouter()


# -----------------------------------------------------------------------
# Utility helpers (stateless, extracted from original app.py)
# -----------------------------------------------------------------------

def _sanitize_model_text(text: str) -> str:
    """Remove leaked meta/process narration from model output."""
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    cleaned = cleaned.replace("**", "")
    cleaned = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    lower = cleaned.lower()
    if any(p in lower for p in LEAKY_MODEL_PATTERNS) and any(
        p in lower for p in VISUAL_UNCLEAR_PATTERNS
    ):
        return ""
    if any(p in lower for p in LEAKY_MODEL_PATTERNS):
        return "Could you clarify what you mean?"
    return cleaned


def _audio_chunk_has_activity(audio_data: bytes) -> bool:
    """Return True if PCM16 chunk likely contains speech."""
    if not audio_data or len(audio_data) < 2:
        return False
    try:
        pcm = array.array("h")
        pcm.frombytes(audio_data)
    except Exception:
        return False
    if not pcm:
        return False
    step = max(1, len(pcm) // 160)
    peak = 0
    threshold = settings.audio_activity_peak_threshold
    for i in range(0, len(pcm), step):
        value = abs(int(pcm[i]))
        if value > peak:
            peak = value
            if peak >= threshold:
                return True
    return False


def _extract_attr(obj, names: tuple[str, ...]):
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def _extract_session_resumption_update(event):
    direct = _extract_attr(
        event, ("session_resumption_update", "sessionResumptionUpdate")
    )
    if direct is not None:
        return direct
    nested = _extract_attr(
        event, ("server_message", "serverMessage", "raw_response", "rawResponse")
    )
    if nested is not None:
        return _extract_attr(
            nested, ("session_resumption_update", "sessionResumptionUpdate")
        )
    return None


def _extract_go_away(event):
    direct = _extract_attr(event, ("go_away", "goAway"))
    if direct is not None:
        return direct
    nested = _extract_attr(
        event, ("server_message", "serverMessage", "raw_response", "rawResponse")
    )
    if nested is not None:
        return _extract_attr(nested, ("go_away", "goAway"))
    return None


def _duration_to_seconds(duration) -> float | None:
    if duration is None:
        return None
    if isinstance(duration, (int, float)):
        return float(duration)
    seconds = getattr(duration, "seconds", None)
    nanos = getattr(duration, "nanos", None)
    if seconds is not None or nanos is not None:
        return float(seconds or 0) + (float(nanos or 0) / 1_000_000_000)
    text = str(duration).strip()
    if text.endswith("s"):
        text = text[:-1]
    try:
        return float(text)
    except ValueError:
        return None


def _is_invalid_argument_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "invalid argument" in message
        or "response_modalities" in message
        or "1007" in message
    )


def _is_normal_close_error(exc: Exception) -> bool:
    stack = [exc]
    seen_ids: set[int] = set()
    while stack:
        current = stack.pop()
        if current is None:
            continue
        ident = id(current)
        if ident in seen_ids:
            continue
        seen_ids.add(ident)
        status_code = getattr(current, "status_code", None)
        try:
            if status_code is not None and int(status_code) == 1000:
                return True
        except Exception:
            pass
        message = str(current).lower()
        if (
            "connectionclosedok" in message
            or "sent 1000 (ok)" in message
            or "received 1000" in message
            or "apierror: 1000" in message
            or message.startswith("1000 none")
            or message == "1000 none."
        ):
            return True
        stack.append(getattr(current, "__cause__", None))
        stack.append(getattr(current, "__context__", None))
    return False


def _is_deadline_expired_error(exc: Exception) -> bool:
    stack = [exc]
    seen_ids: set[int] = set()
    while stack:
        current = stack.pop()
        if current is None:
            continue
        ident = id(current)
        if ident in seen_ids:
            continue
        seen_ids.add(ident)
        status_code = getattr(current, "status_code", None)
        try:
            if status_code is not None and int(status_code) == 1011:
                return True
        except Exception:
            pass
        message = str(current).lower()
        if "1011" in message or "deadline expired" in message:
            return True
        stack.append(getattr(current, "__cause__", None))
        stack.append(getattr(current, "__context__", None))
    return False


# -----------------------------------------------------------------------
# Session handler — replaces nested closures with instance state
# -----------------------------------------------------------------------

class LiveSession:
    """Manages a single WebSocket ↔ ADK live session."""

    def __init__(
        self,
        websocket: WebSocket,
        user_id: str,
        session_id: str,
        voice_name: str | None = None,
    ) -> None:
        self.ws = websocket
        self.user_id = user_id
        self.session_id = session_id
        self.voice_name = voice_name  # Custom voice from client

        self.live_request_queue = LiveRequestQueue()
        self.audio_out: asyncio.Queue[bytes] = asyncio.Queue(
            maxsize=settings.audio_queue_maxsize
        )
        self.json_out: asyncio.Queue[dict] = asyncio.Queue(
            maxsize=settings.json_queue_maxsize
        )
        self.resumption_handle: str | None = (
            session_service.get_cached_resumption_handle(user_id, session_id)
        )
        self.last_audio_input_at: float = 0.0
        self.last_video_forwarded_at: float = 0.0
        self.diarizer = get_diarizer()

    def ws_open(self) -> bool:
        return (
            self.ws.client_state == WebSocketState.CONNECTED
            and self.ws.application_state == WebSocketState.CONNECTED
        )

    # -- output helpers --------------------------------------------------

    def enqueue_transcript(
        self, role: str, text: str, partial: bool = False
    ) -> None:
        cleaned = (
            _sanitize_model_text(text) if role == "model" else (text or "").strip()
        )
        if not cleaned:
            return
        try:
            self.json_out.put_nowait(
                {"type": "transcript", "role": role, "text": cleaned, "partial": partial}
            )
        except asyncio.QueueFull:
            pass

    def enqueue_audio(self, data: bytes | None) -> None:
        if not data:
            return
        try:
            self.audio_out.put_nowait(data)
        except asyncio.QueueFull:
            pass

    def emit_part(self, part, role: str, partial: bool) -> None:
        inline_data = getattr(part, "inline_data", None)
        if inline_data is not None:
            self.enqueue_audio(getattr(inline_data, "data", None))
        audio = getattr(part, "audio", None)
        if audio is not None:
            self.enqueue_audio(getattr(audio, "data", None))
        
        # Skip thought parts (internal reasoning)
        if getattr(part, "thought", False):
            print(f"[DEBUG] Skipping thought=True part")
            return
        
        text = getattr(part, "text", None)
        if text:
            # Debug: print all part attributes to understand structure
            print(f"[DEBUG] Part attributes: {[a for a in dir(part) if not a.startswith('_')]}")
            print(f"[DEBUG] emit_part text: '{text[:100]}...' (role={role}, partial={partial})")
            # Skip text parts - we only want output_transcription for the actual spoken words
            # Text parts from content.parts are usually internal reasoning
            return

    # -- upstream: client → ADK ------------------------------------------

    async def upstream(self) -> None:
        try:
            while True:
                message = await self.ws.receive()
                if message.get("type") == "websocket.disconnect":
                    break

                if "bytes" in message:
                    audio_data = message["bytes"]
                    if _audio_chunk_has_activity(audio_data):
                        self.last_audio_input_at = time.monotonic()
                    self.live_request_queue.send_realtime(
                        types.Blob(mime_type="audio/pcm;rate=16000", data=audio_data)
                    )
                    if self.diarizer is not None:
                        await self.diarizer.feed(audio_data)

                elif "text" in message:
                    try:
                        data = json.loads(message["text"])
                    except (json.JSONDecodeError, TypeError):
                        continue

                    if data.get("type") == "close":
                        break

                    parsed = parse_client_message(data)
                    if parsed is None:
                        continue

                    if isinstance(parsed, TextInput):
                        self.live_request_queue.send_content(
                            types.Content(
                                role="user",
                                parts=[types.Part(text=parsed.content)],
                            )
                        )

                    elif isinstance(parsed, (ImageInput, VideoFrame)):
                        if isinstance(parsed, VideoFrame):
                            if not self._should_forward_video():
                                continue
                            self.last_video_forwarded_at = time.monotonic()
                        try:
                            image_bytes = base64.b64decode(parsed.data)
                        except Exception:
                            continue
                        if parsed.mime_type == "image/jpeg" and (
                            len(image_bytes) < 2 or image_bytes[0:2] != b"\xff\xd8"
                        ):
                            continue
                        self.live_request_queue.send_realtime(
                            types.Blob(mime_type=parsed.mime_type, data=image_bytes)
                        )

                    elif isinstance(parsed, PdfInput):
                        pdf_bytes = base64.b64decode(parsed.data)
                        self.live_request_queue.send_content(
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part(
                                        inline_data=types.Blob(
                                            mime_type="application/pdf",
                                            data=pdf_bytes,
                                        )
                                    ),
                                    types.Part(text=parsed.prompt),
                                ],
                            )
                        )
        except WebSocketDisconnect:
            pass
        finally:
            self.live_request_queue.close()

    def _should_forward_video(self) -> bool:
        if settings.video_min_forward_interval_ms <= 0:
            return True
        now = time.monotonic()
        ms_since_last = (now - self.last_video_forwarded_at) * 1000
        if ms_since_last < settings.video_min_forward_interval_ms:
            return False
        ms_since_audio = (now - self.last_audio_input_at) * 1000
        if (
            settings.video_suppress_during_audio_ms > 0
            and ms_since_audio < settings.video_suppress_during_audio_ms
            and ms_since_last < settings.video_max_staleness_ms
        ):
            return False
        return True

    # -- downstream: ADK → client ----------------------------------------

    async def downstream(self) -> None:
        runner = agent_service.get_runner()
        retry = 0
        while True:
            if not self.ws_open():
                return
            try:
                run_config = agent_service.build_run_config(
                    resume_handle=self.resumption_handle,
                    voice_name=self.voice_name,
                )
                live_events = runner.run_live(
                    session_id=self.session_id,
                    user_id=self.user_id,
                    live_request_queue=self.live_request_queue,
                    run_config=run_config,
                )
                async for event in live_events:
                    if not self.ws_open():
                        return
                    self._handle_event(event)

                # Stream ended — try to resume if possible
                if self.ws_open() and self.resumption_handle:
                    logger.info("Live upstream disconnected; reconnecting with session resumption handle")
                    retry = 0
                    await asyncio.sleep(0.2)
                    continue

                if self.ws_open():
                    self._enqueue_error(
                        "Live connection ended before a resumable handle was available. "
                        "Please reconnect to continue."
                    )
                return

            except WebSocketDisconnect:
                return
            except Exception as exc:
                action = self._classify_downstream_error(exc, retry)
                if action == "resume":
                    retry = 0
                    await asyncio.sleep(0.2)
                    continue
                if action == "reconnect_fresh":
                    retry = 0
                    await asyncio.sleep(0.5)
                    continue
                if action == "retry":
                    retry += 1
                    if retry > settings.max_downstream_retries:
                        self._enqueue_error("Live connection dropped. Please reconnect.")
                        return
                    await asyncio.sleep(min(2 ** retry, 10))
                    continue
                # action == "abort"
                return

    def _handle_event(self, event) -> None:
        """Process a single ADK live event."""
        # Handle transcriptions directly from event (ADK format)
        output_tx_direct = getattr(event, "output_transcription", None)
        if output_tx_direct is not None:
            text = getattr(output_tx_direct, "text", "") or ""
            if text:
                print(f"[AI RESPONSE] {text}")
                self.enqueue_transcript(role="model", text=text, partial=bool(getattr(event, "partial", False)))
        
        input_tx_direct = getattr(event, "input_transcription", None)
        if input_tx_direct is not None:
            text = getattr(input_tx_direct, "text", "") or ""
            if text:
                print(f"[USER INPUT] {text}")
                self.enqueue_transcript(role="user", text=text, partial=bool(getattr(event, "partial", False)))
        
        # Session resumption
        resume_update = _extract_session_resumption_update(event)
        if resume_update is not None:
            resumable = bool(getattr(resume_update, "resumable", False))
            new_handle = _extract_attr(resume_update, ("new_handle", "newHandle"))
            if resumable and new_handle:
                self.resumption_handle = str(new_handle)
                session_service.set_cached_resumption_handle(
                    self.user_id, self.session_id, self.resumption_handle,
                )

        # GoAway
        go_away = _extract_go_away(event)
        if go_away is not None:
            time_left = _duration_to_seconds(
                _extract_attr(go_away, ("time_left", "timeLeft"))
            )
            if time_left is not None:
                logger.info("GoAway received; reconnect due in ~%ss", round(time_left, 3))
            try:
                self.json_out.put_nowait(
                    {"type": "go_away", "timeLeftSeconds": time_left}
                )
            except asyncio.QueueFull:
                pass

        # Interrupted
        if getattr(event, "interrupted", False):
            try:
                self.json_out.put_nowait({"type": "interrupted"})
            except asyncio.QueueFull:
                pass

        partial = bool(getattr(event, "partial", False))
        handled_parts = False

        # Raw Live API shape
        server_content = getattr(event, "server_content", None)
        if server_content is not None:
            output_tx = getattr(server_content, "output_transcription", None)
            if output_tx is not None:
                output_text = getattr(output_tx, "text", "") or ""
                print(f"[DEBUG] output_transcription received: '{output_text}' (partial={partial})")
                if output_text:
                    logger.info("AI Response: %s", output_text)
                self.enqueue_transcript(
                    role="model",
                    text=output_text,
                    partial=partial,
                )
            input_tx = getattr(server_content, "input_transcription", None)
            if input_tx is not None:
                self.enqueue_transcript(
                    role="user",
                    text=getattr(input_tx, "text", "") or "",
                    partial=partial,
                )
            model_turn = getattr(server_content, "model_turn", None)
            model_parts = getattr(model_turn, "parts", None) if model_turn else None
            if model_parts:
                handled_parts = True
                for part in model_parts:
                    if not self.ws_open():
                        return
                    self.emit_part(part=part, role="model", partial=partial)

        # ADK-normalized shape
        content = getattr(event, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not handled_parts and parts:
            role = getattr(content, "role", "model")
            for part in parts:
                if not self.ws_open():
                    return
                self.emit_part(part=part, role=role, partial=partial)

    def _classify_downstream_error(self, exc: Exception, retry: int) -> str:
        """Return an action string: resume, reconnect_fresh, retry, abort."""
        if _is_normal_close_error(exc):
            if self.ws_open() and self.resumption_handle:
                logger.info("Live stream closed normally (1000); reconnecting")
                return "resume"
            logger.info("Live stream closed normally (1000)")
            return "abort"

        if _is_deadline_expired_error(exc):
            logger.info("Live stream deadline expired (1011); reconnecting fresh")
            self.resumption_handle = None
            session_service.clear_cached_resumption_handle(
                self.user_id, self.session_id
            )
            if self.ws_open():
                return "reconnect_fresh"
            return "abort"

        if _is_invalid_argument_error(exc):
            if self.resumption_handle:
                logger.warning(
                    "1007 with active resumption handle — clearing and retrying"
                )
                self.resumption_handle = None
                session_service.clear_cached_resumption_handle(
                    self.user_id, self.session_id
                )
                if self.ws_open():
                    return "retry"
            logger.exception("Live stream rejected (1007)", exc_info=True)
            if self.ws_open():
                self._enqueue_error(
                    "Live API rejected request parameters (1007 invalid argument). "
                    "Use a single response modality (AUDIO) and a valid native-audio "
                    "model such as gemini-2.5-flash-native-audio-latest."
                )
            return "abort"

        logger.exception("Live stream error, retrying", exc_info=True)
        return "retry"

    def _enqueue_error(self, message: str) -> None:
        try:
            self.json_out.put_nowait({"type": "error", "message": message})
        except asyncio.QueueFull:
            pass

    # -- sender: queues → WebSocket --------------------------------------

    async def websocket_sender(self) -> None:
        audio_task = asyncio.create_task(self.audio_out.get())
        json_task = asyncio.create_task(self.json_out.get())
        try:
            while True:
                done, _ = await asyncio.wait(
                    {audio_task, json_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if audio_task in done:
                    data = audio_task.result()
                    audio_task = asyncio.create_task(self.audio_out.get())
                    try:
                        await self.ws.send_bytes(data)
                    except (WebSocketDisconnect, RuntimeError):
                        return
                if json_task in done:
                    payload = json_task.result()
                    json_task = asyncio.create_task(self.json_out.get())
                    try:
                        await self.ws.send_json(payload)
                    except (WebSocketDisconnect, RuntimeError):
                        return
        finally:
            audio_task.cancel()
            json_task.cancel()

    # -- diarization loop ------------------------------------------------

    async def diarization_loop(self) -> None:
        if self.diarizer is None:
            return
        try:
            async for segment in self.diarizer.segments():
                await self.ws.send_json({
                    "type": "diarization",
                    "speaker": segment["speaker"],
                    "text": segment.get("text", ""),
                    "start": segment.get("start"),
                    "end": segment.get("end"),
                })
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    # -- run all loops ---------------------------------------------------

    async def run(self) -> None:
        """Run the full session lifecycle."""
        await session_service.ensure_session(self.user_id, self.session_id)

        if self.resumption_handle:
            logger.info(
                "Using cached session resumption handle for user_id=%s session_id=%s",
                self.user_id,
                self.session_id,
            )

        tasks = [
            asyncio.create_task(self.upstream()),
            asyncio.create_task(self.downstream()),
            asyncio.create_task(self.websocket_sender()),
        ]
        if self.diarizer is not None:
            tasks.append(asyncio.create_task(self.diarization_loop()))

        try:
            await asyncio.gather(*tasks)
        except Exception:
            traceback.print_exc()
        finally:
            for t in tasks:
                t.cancel()
            if self.diarizer is not None:
                await self.diarizer.reset()
            try:
                await self.ws.close()
            except Exception:
                pass


# -----------------------------------------------------------------------
# WebSocket endpoint
# -----------------------------------------------------------------------

@router.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket, user_id: str, session_id: str
) -> None:
    # Extract voice parameter from query string
    voice_name = websocket.query_params.get("voice", None)
    
    await websocket.accept()
    session = LiveSession(websocket, user_id, session_id, voice_name=voice_name)
    await session.run()