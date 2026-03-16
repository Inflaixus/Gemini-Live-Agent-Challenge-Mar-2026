"""Keyword-based RAG retriever over YAML scenario chunks.

Exposes a clean interface: retrieve(query) -> str
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from app.core.config import settings
from .knowledge_loader import load_scenario_chunks

_TOKEN_RE = re.compile(r"[\w\u0600-\u06FF']+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall((text or "").lower())]


def _content_tokens(text: str) -> set[str]:
    stopwords = settings.rag_stopwords
    return {t for t in _tokenize(text) if len(t) > 1 and t not in stopwords}


def _is_ambiguous_query(query: str) -> bool:
    tokens = _content_tokens(query)
    if not tokens:
        return True
    if len(tokens) == 1:
        token = next(iter(tokens))
        if token in {"what", "why", "how", "huh", "um", "okay"}:
            return True
    return False


def _match_query(query: str, chunk: dict[str, Any]) -> float:
    """Score how well a query matches a chunk's ask_patterns and topic."""
    query_lower = query.lower().strip()
    query_terms = _content_tokens(query_lower)
    if not query_terms:
        return 0.0

    score = 0.0
    exact_w = settings.rag_exact_phrase_weight
    overlap_w = settings.rag_token_overlap_weight
    topic_w = settings.rag_topic_weight

    patterns = chunk.get("ask_patterns", [])
    for pattern in patterns:
        pattern_lower = str(pattern).lower().strip()
        pattern_terms = _content_tokens(pattern_lower)
        if not pattern_terms:
            continue
        if pattern_lower and pattern_lower in query_lower:
            score += exact_w
            continue
        overlap = len(query_terms & pattern_terms)
        if overlap:
            coverage = overlap / max(len(pattern_terms), 1)
            score += overlap_w * coverage

    topic = chunk.get("topic", "")
    topic_terms = _content_tokens(str(topic).replace("_", " "))
    if topic_terms:
        score += topic_w * len(query_terms & topic_terms)

    return score


class KnowledgeBase:
    """In-memory RAG over YAML scenario files.

    Initialised lazily — call load() explicitly before first use.
    """

    def __init__(self) -> None:
        self._chunks: list[dict[str, Any]] = []
        self._always_visible: list[dict[str, Any]] = []
        self._loaded = False

    def load(self, scenario: str) -> None:
        """Load chunks for the given scenario."""
        self._chunks = load_scenario_chunks(scenario)
        self._always_visible = [
            c for c in self._chunks
            if c.get("visibility_rule") == "always_available"
        ]
        self._loaded = True

    def retrieve(self, query: str, top_k: int | None = None) -> str:
        """Retrieve relevant KB chunks for a given query."""
        if not self._loaded:
            return ""
        if not query.strip() or _is_ambiguous_query(query):
            return ""

        if top_k is None:
            top_k = settings.rag_top_k
        min_score = settings.rag_min_score

        scored: list[tuple[float, dict]] = []
        for chunk in self._chunks:
            vis = chunk.get("visibility_rule", "")
            if vis == "volunteer_opening_only":
                continue
            s = _match_query(query, chunk)
            if s >= min_score:
                scored.append((s, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [c for _, c in scored[:top_k]]

        if top:
            for av in self._always_visible:
                if av not in top:
                    top.append(av)

        if not top:
            return "No relevant facts found in KB."

        parts = ["RETRIEVED FACTS:"]
        for chunk in top:
            content = chunk.get("content", "")
            if isinstance(content, list):
                content = yaml.dump(content, allow_unicode=True)
            parts.append(f"[{chunk.get('chunk_id', 'unknown')}]\n{content}")

        return "\n\n".join(parts)

    def get_opening(self) -> str:
        """Get the scenario opening statement."""
        for chunk in self._chunks:
            if chunk.get("visibility_rule") == "volunteer_opening_only":
                return chunk.get("content", "").strip()
        return ""
