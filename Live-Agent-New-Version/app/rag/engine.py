from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import re

from .scope import (
    detect_smalltalk_intents, smalltalk_reply,
    is_out_of_scope, looks_like_dental_osce, OUT_OF_SCOPE_REPLY
)
from .controller import SessionState, update_state_from_doctor, maybe_fire_nudge
from .retriever import Retriever, chunk_text


FORBIDDEN_SMALLTALK_LEAK = ["wedding", "married", "amalgam", "filling", "diabetes", "mercury"]

@dataclass
class EngineConfig:
    top_k: int = 6
    sim_threshold: float = 0.30
    temperature: float = 0.25


def dentist_asking_about_topic(doctor_text: str, topic: str, topic_bank: dict[str, list[str]]) -> bool:
    t = doctor_text.lower()
    patterns = topic_bank.get(topic, [])
    if not patterns:
        # no patterns defined -> we can't confidently say dentist asked about it
        return False
    
    # Check if any pattern matches
    matched = any(p.lower() in t for p in patterns)
    
    # Debug logging
    # Uncomment to debug:
    # if matched:
    #     print(f"[DEBUG] Topic '{topic}' matched with patterns: {[p for p in patterns if p.lower() in t]}")
    
    return matched


def build_context(emotional_chunk: dict | None, retrieved: list[tuple[float, dict]], min_confidence: float = 0.30) -> str:
    """
    Build context with confidence filtering.
    Only include chunks above minimum confidence threshold.
    """
    blocks = []
    if emotional_chunk:
        blocks.append("EMOTIONAL PROFILE:\n" + chunk_text(emotional_chunk).strip())

    if retrieved:
        # Filter by confidence
        high_conf = [(s, c) for s, c in retrieved if s >= min_confidence]
        
        if high_conf:
            blocks.append("RETRIEVED FACTS (use only these):")
            for score, ch in high_conf:
                topic = ch.get("topic", "")
                blocks.append(f"- [confidence={score:.3f} topic={topic}] {chunk_text(ch).strip()}")
        else:
            # No high-confidence matches
            blocks.append("RETRIEVED FACTS: [No high-confidence matches found]")

    return "\n\n".join(blocks).strip()

def patient_user_prompt(doctor_text: str, history_text: str, context: str, nudge: str | None) -> str:
    return f"""CONVERSATION SO FAR (for continuity only; do not invent facts from it):
{history_text if history_text else "[none]"}

DENTIST SAID (latest):
{doctor_text}

{context if context else "RETRIEVED FACTS: [none]"}

Rules:
- Answer ONLY using the retrieved facts above.
- Use conversation history only to avoid repeating yourself and to stay consistent in tone.
- Vary your wording naturally - don't use the exact same phrasing as before.
- If you've already answered this topic, acknowledge briefly and don't repeat the full answer unless asked again.
- Keep responses conversational and natural (1-3 sentences max).

If you need to add a nudge, add it as a patient question at the end.
NUDGE (optional): {nudge if nudge else "[none]"}
"""

def smalltalk_system_prompt(global_policy_text: str) -> str:
    return global_policy_text.strip() + """

SMALLTALK PREFIX MODE:
- You MUST NOT introduce any new personal details, occupations, hobbies, medical conditions,
  or constraints unless they are explicitly present in the retrieved KB or triggered by a nudge.
  If such details are not in context, do not invent them.
- Do not repeat information you already stated earlier in the conversation unless the dentist asks about it again.
  If the dentist moves forward, move forward with them.
- Generate ONLY a short polite prefix (max 1 sentence).
- Do NOT mention any scenario facts (no wedding, fillings, diabetes, mercury, etc.).
- Do NOT ask follow-up questions unless the dentist asked one.
- Do NOT include speaker labels like DOCTOR:, PATIENT:.
"""

def smalltalk_user_prompt(intents: set[str], doctor_text: str) -> str:
    return f"""DENTIST MESSAGE:
{doctor_text}

Detected intents: {sorted(intents)}

Write a natural patient smalltalk prefix only (one short sentence)."""


def llm_smalltalk_prefix(intents, doctor_text, global_policy_text, llm_call) -> str:
    if not intents:
        return ""
    system = smalltalk_system_prompt(global_policy_text)
    user = smalltalk_user_prompt(intents, doctor_text)
    prefix = llm_call(system, user, 0.5).strip()
    # safety strip labels
    prefix = re.sub(r"^\s*(DOCTOR|DENTIST|PATIENT)\s*:\s*", "", prefix, flags=re.I).strip()
    # safety prevent scenario leakage from prefix
    if any(w in prefix.lower() for w in FORBIDDEN_SMALLTALK_LEAK):
        # fallback safe prefix based on intent
        if "congrats" in intents:
            return "Thank you."
        if "greet" in intents:
            return "Hello."
        return "Thanks."
    return prefix

def remember_and_return(state, doctor_text: str, patient_text: str) -> str:
    state.conversation_history.append(("doctor", doctor_text))
    state.conversation_history.append(("patient", patient_text))
    return patient_text

def looks_like_consultation_dialogue(text: str) -> bool:
    t = text.lower()
    cues = [
        "i don't understand", "i dont understand", "what do you mean",
        "can you explain", "explain again", "pros and cons", "advantages", "disadvantages",
        "downside", "benefit", "risk", "is it safe", "what happens if",
        "how long", "how many visits", "timeline", "appointments", "schedule",
        "how much", "cost", "price", "budget",
        "okay", "got it", "makes sense"
    ]
    return any(c in t for c in cues)

def is_confirmation_question(text: str) -> bool:
    t = text.lower().strip()
    patterns = [
        "is that right",
        "is that correct",
        "right?",
        "correct?",
        "you'd like",
        "you would like",
        "i understand you want",
        "i understand you'd like"
    ]
    return any(p in t for p in patterns)

def build_chat_history(state, max_turns=6):
    history = state.conversation_history[-max_turns:]
    formatted = []
    for role, text in history:
        if role == "doctor":
            formatted.append(f"Dentist said: {text}")
        else:
            formatted.append(f"Patient said: {text}")
    return "\n".join(formatted)

def should_block_repeat(state: SessionState, doctor_text: str, topic_bank: dict[str, list[str]]) -> bool:
    # If reply reuses a topic we've already covered, only allow it if dentist asked about it again.
    for topic in state.last_reply_topics:
        if topic in state.mentioned_topics:
            if not dentist_asking_about_topic(doctor_text, topic, topic_bank):
                if hasattr(state, 'debug_mode') and state.debug_mode:
                    print(f"[DEBUG] Blocking repeat for topic: {topic}")
                    print(f"[DEBUG] Patterns for this topic: {topic_bank.get(topic, [])}")
                    print(f"[DEBUG] Doctor text: {doctor_text[:100]}")
                return True
    return False

def filter_repeated_topics(matches: list[tuple[float, dict]], state: SessionState, doctor_text: str, topic_bank: dict[str, list[str]]) -> list[tuple[float, dict]]:
    """
    Filter out chunks with topics that were already mentioned, 
    UNLESS the dentist is asking about that topic again.
    
    This prevents repetition while allowing re-answering when asked.
    """
    filtered = []
    for score, chunk in matches:
        topic = chunk.get("topic")
        if not topic:
            # No topic → include it
            filtered.append((score, chunk))
            continue
        
        if topic not in state.mentioned_topics:
            # Topic not mentioned before → include it
            filtered.append((score, chunk))
            continue
        
        # Topic was mentioned before → check if dentist is asking about it again
        if dentist_asking_about_topic(doctor_text, topic, topic_bank):
            # Dentist asked again → include it
            if hasattr(state, 'debug_mode') and state.debug_mode:
                print(f"[DEBUG] Re-including topic '{topic}' - dentist asked again")
            filtered.append((score, chunk))
        else:
            # Topic already covered and dentist NOT asking → filter it out
            if hasattr(state, 'debug_mode') and state.debug_mode:
                print(f"[DEBUG] Filtering out repeated topic: {topic}")
    
    return filtered

def patient_reply_rag(
    doctor_text: str,
    state: SessionState,
    global_policy_text: str,
    opening_chunk: dict | None,
    emotional_chunk: dict | None,
    nudges: list[dict],
    case_retriever: Retriever,
    llm_call: Callable[[str, str, float], str],
    config: EngineConfig,
    topic_bank: dict[str, list[str]],  
    global_dental_retriever: Retriever | None = None,
) -> str:
    doctor_text = doctor_text.strip()

    # 1) Detect smalltalk intents and generate dynamic prefix via LLM (Option B)
    intents = detect_smalltalk_intents(doctor_text)
    prefix = llm_smalltalk_prefix(intents, doctor_text, global_policy_text, llm_call) if intents else ""

    # 2) Hard out-of-scope block ONLY for truly unrelated topics
    if is_out_of_scope(doctor_text):
        msg = OUT_OF_SCOPE_REPLY
        if prefix:
            msg = f"{prefix} {msg}".strip()
        return remember_and_return(state, doctor_text, msg)

    # 3) If message is smalltalk-only (no dental cues and no consultation dialogue), reply with prefix only
    if intents and not looks_like_dental_osce(doctor_text) and not looks_like_consultation_dialogue(doctor_text):
        msg = prefix or "Hello."
        return remember_and_return(state, doctor_text, msg)

    # 4) First patient turn behavior
    if not state.opening_done:
        state.opening_done = True

        opening = chunk_text(opening_chunk).strip() if opening_chunk else ""
        if not opening:
            raise ValueError("Opening chunk is missing/empty for this scenario.")

        # If dentist asked a confirmation question, answer confirmation (don’t repeat the opening)
        if is_confirmation_question(doctor_text):
            msg = "Yes, that’s right."
            if prefix:
                msg = f"{prefix} {msg}".strip()
            return remember_and_return(state, doctor_text, msg)

        # Otherwise: opening statement (optionally with smalltalk prefix)
        msg = opening
        if prefix:
            msg = f"{prefix} {msg}".strip()
        return remember_and_return(state, doctor_text, msg)

    # 5) Update controller state + maybe fire nudge
    update_state_from_doctor(doctor_text, state)
    nudge = maybe_fire_nudge(nudges, state) or None

    # 6) Retrieval: case first
    case_matches = case_retriever.search(doctor_text, top_k=config.top_k)
    case_matches = [(s, c) for (s, c) in case_matches if s >= config.sim_threshold]

    matches = case_matches

    # Debug logging (optional - can be toggled)
    if hasattr(state, 'debug_mode') and state.debug_mode:
        print(f"[DEBUG] Case matches: {len(case_matches)}")
        for s, c in case_matches[:3]:
            print(f"  - {s:.3f}: {c.get('topic', 'unknown')}")

    # Fallback: global dental
    if not matches and global_dental_retriever is not None:
        gd_matches = global_dental_retriever.search(doctor_text, top_k=config.top_k)
        gd_matches = [(s, c) for (s, c) in gd_matches if s >= config.sim_threshold]
        matches = gd_matches
        
        if hasattr(state, 'debug_mode') and state.debug_mode and gd_matches:
            print(f"[DEBUG] Using global dental fallback: {len(gd_matches)} matches")

    # Filter out repeated topics (unless dentist asks about them again)
    if hasattr(state, 'debug_mode') and state.debug_mode:
        print(f"[DEBUG] mentioned_topics before filtering: {state.mentioned_topics}")
    
    matches = filter_repeated_topics(matches, state, doctor_text, topic_bank)
    
    if hasattr(state, 'debug_mode') and state.debug_mode:
        print(f"[DEBUG] After filtering: {len(matches)} matches")

  # ---- Track topics from retrieved chunks ----
    reply_topics = {c.get("topic") for _, c in matches if c.get("topic")}
    state.last_reply_topics = reply_topics
    
    # Only add topics to mentioned_topics, excluding always-available ones
    topics_to_remember = {t for t in reply_topics if t != "emotional_profile"}
    state.mentioned_topics |= topics_to_remember
    # --------------------------------------------

    # 7) If nothing retrieved, do NOT refuse; allow “natural fallback” in system prompt
    # We still proceed to LLM with empty matches (so it can say "I’m not sure" or ask clarification).
    system = global_policy_text.strip()
    context = build_context(emotional_chunk, matches)  # can be empty
    history_text = build_chat_history(state, max_turns=4)  # formatted as Dentist said/Patient said
    user = patient_user_prompt(doctor_text, history_text, context, nudge)

    # 8) Call LLM
    reply = llm_call(system, user, config.temperature).strip()

    # 9) Strip role labels (anti-contamination)
    reply = re.sub(r"^\s*(DOCTOR|DENTIST|PATIENT)\s*:\s*", "", reply, flags=re.I).strip()

    # 10) Prefix + remember
    if prefix:
        reply = f"{prefix} {reply}".strip()

    return remember_and_return(state, doctor_text, reply)