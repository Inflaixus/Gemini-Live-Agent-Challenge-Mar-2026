"""Patient agent definition — ADK Agent with dynamic prompt loading.

Nothing heavy runs at import time. Call create_agent() explicitly.
"""

from __future__ import annotations

from pathlib import Path

from google.adk.agents import Agent

from app.core.config import settings
from app.rag.knowledge_loader import load_general_prompt
from app.rag.retriever import KnowledgeBase
from . import agent_tools

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts" / "system"


def _load_prompt_template() -> str:
    """Read the system prompt template from disk."""
    path = _PROMPT_DIR / "patient_system_prompt.txt"
    return path.read_text(encoding="utf-8")


def create_agent(scenario: str | None = None) -> tuple[Agent, KnowledgeBase]:
    """Build and return the ADK Agent + its KnowledgeBase.

    This is the single place where the agent, prompt, and KB are wired
    together.  Called once during app startup — never at import time.
    """
    scenario = scenario or settings.default_scenario

    # Load RAG knowledge base
    kb = KnowledgeBase()
    kb.load(scenario)

    # Build system prompt
    general_context = load_general_prompt()
    prompt_template = _load_prompt_template()
    system_instruction = prompt_template.replace(
        "{general_context}", general_context
    )

    # RAG tool closure
    def search_patient_kb(query: str) -> dict:
        """Search the patient knowledge base for relevant information.

        Use this tool silently whenever the dentist asks about the patient's
        medical history, symptoms, allergies, dental history, concerns, or
        any personal information. Never narrate that tool usage to the dentist.

        Args:
            query: The dentist's question or topic to search for.

        Returns:
            Retrieved facts from the patient knowledge base.
        """
        result = kb.retrieve(query)
        if not result:
            result = "No relevant facts found in KB."
        return {"retrieved_context": result}

    agent = Agent(
        name="bilingual_audio_agent",
        model=settings.agent_model,
        description=(
            "An OSCE patient agent that role-plays a dental patient, "
            "answering questions based on scenario knowledge base."
        ),
        instruction=system_instruction,
        tools=[
            agent_tools.detect_language,
            agent_tools.introduce_agent,
            agent_tools.check_out_of_scope,
            search_patient_kb,
        ],
    )
    return agent, kb
