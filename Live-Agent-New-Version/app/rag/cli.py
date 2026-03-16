import sys
import asyncio
from pathlib import Path
from collections import defaultdict

from .kb_loader import load_kb
from .retriever import Retriever
from .controller import SessionState
from .engine import patient_reply_rag, EngineConfig
from .llm import llm_call_gemini


def build_topic_bank(chunks: list[dict]) -> dict[str, list[str]]:
    bank = defaultdict(list)
    for c in chunks:
        topic = c.get("topic")
        if not topic:
            continue
        bank[topic].extend(c.get("ask_patterns", []) or [])
    return {topic: list(dict.fromkeys(pats)) for topic, pats in bank.items()}


def _load_everything():
    """Shared KB + retriever setup for both text and live modes."""
    kb_root = Path("kb")
    case_id = "OSCE_AMALGAM_PREWEDDING_001"

    kb = load_kb(kb_root, case_id, enable_global_dental=True)
    topic_bank = build_topic_bank(kb.case_chunks)
    print("1) KB loaded")

    print("2) Building CASE retriever...")
    case_retriever = Retriever(kb.case_chunks)
    print("3) CASE retriever ready")

    print("4) Building GLOBAL retriever...")
    global_dental_retriever = (
        Retriever(kb.global_dental_chunks) if kb.global_dental_chunks else None
    )
    print("5) GLOBAL retriever ready")

    state = SessionState()
    state.debug_mode = True
    config = EngineConfig(top_k=6, sim_threshold=0.25, temperature=0.2)

    return kb, topic_bank, case_retriever, global_dental_retriever, state, config


def main_text():
    """Original text-based CLI (type as doctor, get text replies)."""
    kb, topic_bank, case_retriever, global_dental_retriever, state, config = (
        _load_everything()
    )
    print("6) OSCE Patient Chatbot (Doctor -> Patient). Ctrl+C to exit.\n")

    while True:
        doctor = input("DOCTOR: ").strip()
        if not doctor:
            continue

        reply = patient_reply_rag(
            doctor_text=doctor,
            state=state,
            global_policy_text=kb.policy_text,
            opening_chunk=kb.opening_chunk,
            emotional_chunk=kb.emotional_chunk,
            nudges=kb.nudges,
            case_retriever=case_retriever,
            llm_call=llm_call_gemini,
            config=config,
            global_dental_retriever=global_dental_retriever,
            topic_bank=topic_bank,
        )
        print(f"PATIENT: {reply}\n")


def main_live():
    """Live voice mode — speak as doctor, patient replies with voice."""
    from .live_session import LivePatientSession

    kb, topic_bank, case_retriever, global_dental_retriever, state, config = (
        _load_everything()
    )
    print("6) OSCE Live Voice Patient. Speak as the doctor. Ctrl+C to exit.\n")

    session = LivePatientSession(
        state=state,
        global_policy_text=kb.policy_text,
        opening_chunk=kb.opening_chunk,
        emotional_chunk=kb.emotional_chunk,
        nudges=kb.nudges,
        case_retriever=case_retriever,
        config=config,
        topic_bank=topic_bank,
        global_dental_retriever=global_dental_retriever,
        voice="Kore",
    )

    try:
        asyncio.run(session.run())
    except KeyboardInterrupt:
        print("\n[LIVE] Session ended.")
    finally:
        session.cleanup()


def main():
    if "--live" in sys.argv:
        main_live()
    else:
        main_text()


if __name__ == "__main__":
    main()
