"""
Gemini LLM wrappers.
- llm_call_gemini: text call used by the RAG engine (retriever context -> response)
- DEFAULT_MODEL / client: shared by live_session.py for the Live API audio
"""
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # loads .env file automatically

# Live API model (native audio — voice in/out)
DEFAULT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")

# Text model (used by engine for smalltalk prefix, etc.)
TEXT_MODEL = os.getenv("TEXT_MODEL", "gemini-2.5-flash")

# Shared client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))


def llm_call_gemini(system: str, user: str, temperature: float = 0.2) -> str:
    """
    Text-based Gemini call — drop-in replacement for Ollama.
    Same signature: (system, user, temperature) -> str
    """
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
        ),
    )
    return (response.text or "").strip()
