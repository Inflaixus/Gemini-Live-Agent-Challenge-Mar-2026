"""WebSocket protocol — structured message schemas.

All messages between client and server pass through these types.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


# -----------------------------------------------------------------------
# Server → Client messages
# -----------------------------------------------------------------------

@dataclass(slots=True)
class TranscriptMessage:
    role: str
    text: str
    partial: bool = False
    type: str = "transcript"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ErrorMessage:
    message: str
    type: str = "error"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class InterruptedMessage:
    type: str = "interrupted"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GoAwayMessage:
    timeLeftSeconds: float | None = None
    type: str = "go_away"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DiarizationSegment:
    speaker: str
    text: str
    start: float | None = None
    end: float | None = None
    type: str = "diarization"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# -----------------------------------------------------------------------
# Client → Server message parsing
# -----------------------------------------------------------------------

@dataclass(slots=True)
class TextInput:
    content: str


@dataclass(slots=True)
class ImageInput:
    data: str          # base64
    mime_type: str = "image/jpeg"


@dataclass(slots=True)
class VideoFrame:
    data: str          # base64
    mime_type: str = "image/jpeg"


@dataclass(slots=True)
class PdfInput:
    data: str          # base64
    prompt: str = "Summarize this document."


def parse_client_message(raw: dict[str, Any]) -> TextInput | ImageInput | VideoFrame | PdfInput | None:
    """Parse a JSON message from the client into a typed object.

    Returns None for unrecognised or malformed messages.
    """
    msg_type = raw.get("type")

    if msg_type == "text":
        content = raw.get("content")
        if not content or not isinstance(content, str) or not content.strip():
            return None
        return TextInput(content=content.strip())

    if msg_type in ("image", "video_frame"):
        data = raw.get("data")
        if not data or not isinstance(data, str) or len(data) < 100:
            return None
        mime = raw.get("mimeType", "image/jpeg")
        if msg_type == "video_frame":
            return VideoFrame(data=data, mime_type=mime)
        return ImageInput(data=data, mime_type=mime)

    if msg_type == "pdf":
        data = raw.get("data")
        if not data:
            return None
        prompt = (raw.get("prompt") or "").strip() or "Summarize this document."
        return PdfInput(data=data, prompt=prompt)

    if msg_type == "close":
        # Sentinel — caller should break the loop.
        return None

    return None
