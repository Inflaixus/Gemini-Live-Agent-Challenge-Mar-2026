"""Session management and resumption handle caching."""

from __future__ import annotations

import time

from google.adk.sessions import InMemorySessionService

from app.core.config import settings
from app.core.constants import APP_NAME

# ADK session store
_session_service = InMemorySessionService()

# In-memory resumption handle cache: (user_id, session_id) -> {handle, expires_at}
_resumption_cache: dict[tuple[str, str], dict[str, float | str]] = {}


def get_adk_session_service() -> InMemorySessionService:
    return _session_service


async def ensure_session(user_id: str, session_id: str):
    """Return an existing session or create a new one."""
    session = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id,
    )
    if session is None:
        session = await _session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id,
        )
    return session


def get_cached_resumption_handle(user_id: str, session_id: str) -> str | None:
    key = (user_id, session_id)
    cached = _resumption_cache.get(key)
    if not cached:
        return None
    expires_at = float(cached.get("expires_at", 0))
    if expires_at <= time.time():
        _resumption_cache.pop(key, None)
        return None
    handle = str(cached.get("handle", "")).strip()
    return handle or None


def set_cached_resumption_handle(
    user_id: str, session_id: str, handle: str | None
) -> None:
    if not handle:
        return
    _resumption_cache[(user_id, session_id)] = {
        "handle": handle,
        "expires_at": time.time() + settings.session_resumption_handle_ttl_seconds,
    }


def clear_cached_resumption_handle(user_id: str, session_id: str) -> None:
    _resumption_cache.pop((user_id, session_id), None)
