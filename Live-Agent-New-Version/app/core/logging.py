"""Centralized logging configuration."""

import logging
import warnings


class _SuppressBenignADK1000Close(logging.Filter):
    """Hide known-benign ADK live-flow close logs for websocket code 1000."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage().lower()
        except Exception:
            return True
        return "unexpected error occurred in live flow: 1000" not in message


def setup_logging() -> None:
    """Configure application-wide logging. Call once at startup."""
    logging.basicConfig(level=logging.INFO)
    warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
    logging.getLogger(
        "google_adk.google.adk.flows.llm_flows.base_llm_flow"
    ).addFilter(_SuppressBenignADK1000Close())


def get_logger(name: str = "adiou") -> logging.Logger:
    return logging.getLogger(name)
