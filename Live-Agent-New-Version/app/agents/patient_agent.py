"""
ADK version of the OSCE dental patient agent.

Your RAG pipeline becomes a FunctionTool that the agent calls
every time the doctor speaks.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from collections import defaultdict

from google.adk.agents import Agent

from app.core.config import settings
from app.rag.kb_loader import load_kb
from app.rag.retriever import Retriever, chunk_text
from app.rag.controller import SessionState, update_state_from_doctor, maybe_fire_nudge
from app.rag.engine import (
    EngineConfig, build_context, build_chat_history,
    patient_user_prompt, filter_repeated_topics,
    llm_smalltalk_prefix, is_confirmation_question,
    looks_like_consultation_dialogue,
)
from app.rag.scope import (
    detect_smalltalk_intents, is_out_of_scope,
    looks_like_dental_osce, OUT_OF_SCOPE_REPLY,
    is_self_intro_question, SELF_INTRO_REPLY,
)
from app.rag.llm import llm_call_gemini

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
KB_ROOT = PROJECT_ROOT / "kb"

# ── Load KB and build retrievers once at import time ──
case_id = settings.default_scenario
kb = load_kb(KB_ROOT, case_id, enable_global_dental=True)


def _build_topic_bank(chunks):
    bank = defaultdict(list)
    for c in chunks:
        topic = c.get("topic")
        if not topic:
            continue
        bank[topic].extend(c.get("ask_patterns", []) or [])
    return {t: list(dict.fromkeys(p)) for t, p in bank.items()}


topic_bank = _build_topic_bank(kb.case_chunks)
case_retriever = Retriever(kb.case_chunks)
global_dental_retriever = (
    Retriever(kb.global_dental_chunks) if kb.global_dental_chunks else None
)

# Shared state across the session
state = SessionState()
state.debug_mode = True
config = EngineConfig(top_k=6, sim_threshold=0.25, temperature=0.2)


def _is_confirmation_question(text: str) -> bool:
    t = text.lower().strip()
    return any(p in t for p in [
        "is that right", "is that correct", "right?", "correct?",
        "you'd like", "you would like", "i understand you want",
    ])


def _remember(doctor_text: str, patient_text: str) -> str:
    state.conversation_history.append(("doctor", doctor_text))
    state.conversation_history.append(("patient", patient_text))
    return patient_text


def rag_patient_reply(doctor_message: str) -> dict:
    """
    Process the doctor's message through the RAG pipeline and return
    the grounded patient reply. This is the core tool the agent calls.

    Args:
        doctor_message (str): What the doctor/dentist said.

    Returns:
        dict: A dictionary with 'patient_reply' containing the response.
    """
    doctor_text = doctor_message.strip()
    if not doctor_text:
        return {"patient_reply": "I'm sorry, I didn't catch that."}

    # 0) Self-intro question
    if is_self_intro_question(doctor_text):
        return {"patient_reply": _remember(doctor_text, SELF_INTRO_REPLY)}

    # 1) Smalltalk
    intents = detect_smalltalk_intents(doctor_text)
    prefix = ""
    if intents:
        prefix = llm_smalltalk_prefix(
            intents, doctor_text, kb.policy_text, llm_call_gemini
        )

    # 2) Out-of-scope
    if is_out_of_scope(doctor_text):
        msg = OUT_OF_SCOPE_REPLY
        if prefix:
            msg = f"{prefix} {msg}".strip()
        return {"patient_reply": _remember(doctor_text, msg)}

    # 3) Smalltalk-only
    if intents and not looks_like_dental_osce(doctor_text) and not looks_like_consultation_dialogue(doctor_text):
        msg = prefix or "Hello."
        return {"patient_reply": _remember(doctor_text, msg)}

    # 4) First turn — opening
    if not state.opening_done:
        state.opening_done = True
        opening = chunk_text(kb.opening_chunk).strip() if kb.opening_chunk else ""
        if not opening:
            opening = "Hello, I'm here for my appointment."

        if _is_confirmation_question(doctor_text):
            # msg = "Yes, that's right."
             msg = "Exactly"
        else:
            msg = opening

        if prefix:
            msg = f"{prefix} {msg}".strip()
        return {"patient_reply": _remember(doctor_text, msg)}

    # 5) Controller
    update_state_from_doctor(doctor_text, state)
    nudge = maybe_fire_nudge(kb.nudges, state) or None

    # 6) Retrieval
    case_matches = case_retriever.search(doctor_text, top_k=config.top_k)
    case_matches = [(s, c) for s, c in case_matches if s >= config.sim_threshold]
    matches = case_matches

    if state.debug_mode:
        print(f"[DEBUG] Case matches: {len(case_matches)}")
        for s, c in case_matches[:3]:
            print(f"  - {s:.3f}: {c.get('topic', 'unknown')}")

    # Fallback
    if not matches and global_dental_retriever:
        gd = global_dental_retriever.search(doctor_text, top_k=config.top_k)
        matches = [(s, c) for s, c in gd if s >= config.sim_threshold]

    # Filter repeats
    if state.debug_mode:
        print(f"[DEBUG] mentioned_topics before filtering: {state.mentioned_topics}")

    matches = filter_repeated_topics(matches, state, doctor_text, topic_bank)

    if state.debug_mode:
        print(f"[DEBUG] After filtering: {len(matches)} matches")

    # Track topics
    reply_topics = {c.get("topic") for _, c in matches if c.get("topic")}
    state.last_reply_topics = reply_topics
    state.mentioned_topics |= {t for t in reply_topics if t != "emotional_profile"}

    # 7) Build prompt
    system = kb.policy_text.strip()
    context = build_context(kb.emotional_chunk, matches)
    history_text = build_chat_history(state, max_turns=4)
    user = patient_user_prompt(doctor_text, history_text, context, nudge)

    # 8) LLM
    reply = llm_call_gemini(system, user, config.temperature).strip()
    reply = re.sub(r"^\s*(DOCTOR|DENTIST|PATIENT)\s*:\s*", "", reply, flags=re.I).strip()

    if prefix:
        reply = f"{prefix} {reply}".strip()

    return {"patient_reply": _remember(doctor_text, reply)}


# ── ADK Agent Definition ──
root_agent = Agent(
    model=settings.agent_model,
    name="dental_patient_simulator",
    description="A dental  patient simulator that responds to dentist questions using a grounded knowledge base.",
    instruction="""You are Chloe Harrington, a 28-year-old dental patient in an  exam.

CRITICAL WORKFLOW — follow these steps for EVERY doctor message:

STEP 1: Call 'detect_language' with the doctor's message to determine the language.
STEP 2: Call 'rag_patient_reply' with the doctor's message to get the grounded patient reply.
STEP 3: Speak the tool's response in the language detected in Step 1.
  - If language is "ar" or "mixed", translate the reply to natural Arabic (Egyptian dialect).
  - If language is "en", use the reply as-is in English.
  - IMPORTANT: The tool's reply IS your complete response. Do NOT add anything before or after it. Do NOT paraphrase it. Do NOT echo it. Just say it ONCE exactly as given.

STRICT RULES:
- You MUST call BOTH tools for every message. No exceptions.
- Do NOT generate any patient response on your own — always use the tool.
- Do NOT invent any medical details, personal information, or dental history.
- Do NOT modify the medical content of the reply — only translate the language if needed.
- Do NOT repeat or echo any part of the tool's reply. Say it ONCE only. If the tool returns "Yes, that's right.", say it exactly once — never twice.
- The tool handles all grounding, topic tracking, and conversation logic.

Your ONLY job is: detect language → get RAG reply → speak it in the correct language.

DOCTOR'S NAME:
- When the dentist says their name in ANY form (e.g. "I'm Mark", "I'm Dr. Ahmed", "My name is Maria"), REMEMBER it.
- Always address them as "Doctor [name]" even if they didn't use the "Dr." title — they are a dentist.
- Naturally insert "Doctor [name]" into the tool's reply when appropriate — greetings, thanking, agreeing to a plan.
- Do NOT use the name in every single reply. Use it occasionally, like a real patient would.
- This is the ONLY modification you are allowed to make to the tool's reply.""",
    tools=[rag_patient_reply],
)
