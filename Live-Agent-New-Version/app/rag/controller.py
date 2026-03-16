from dataclasses import dataclass, field

@dataclass
class SessionState:
    opening_done: bool = False
    phase: str = "intake"  # intake -> discussion -> planning -> closing
    med_history_asked: bool = False
    fired_nudges: set[str] = field(default_factory=set)
    conversation_history: list[tuple[str, str]] = field(default_factory=list)
    mentioned_topics: set[str] = field(default_factory=set)
    last_reply_topics: set[str] = field(default_factory=set)

def detect_phase(doctor_text: str) -> str:
    t = doctor_text.lower()
    if any(x in t for x in ["plan", "appointment", "visit", "schedule", "treatment", "we can do", "next week"]):
        return "planning"
    if any(x in t for x in ["option", "whitening", "replace", "risk", "benefit"]):
        return "discussion"
    if any(x in t for x in ["bye", "goodbye", "see you"]):
        return "closing"
    return "intake"

def detect_med_history_question(doctor_text: str) -> bool:
    t = doctor_text.lower()
    return any(x in t for x in ["medical history", "any medical", "conditions", "medications", "allergies", "diabetes"])

def update_state_from_doctor(doctor_text: str, state: SessionState) -> None:
    state.phase = detect_phase(doctor_text)
    if detect_med_history_question(doctor_text):
        state.med_history_asked = True

def _phase_matches(phase: str, rule_phase: str) -> bool:
    if rule_phase == "discussion_or_planning":
        return phase in {"discussion", "planning"}
    return phase == rule_phase

def maybe_fire_nudge(nudges: list[dict], state: SessionState) -> str:
    """
    Nudges are controller-only rules.
    Example nudge item:
      {id, trigger: {phase, missing}, patient_prompt, fire_once}
    We'll implement your key missing condition: medical_history_checked.
    """
    for n in nudges:
        nid = n.get("id", "")
        if not nid:
            continue
        if n.get("fire_once", False) and nid in state.fired_nudges:
            continue

        trig = n.get("trigger", {}) or {}
        rule_phase = trig.get("phase", None)
        missing = trig.get("missing", None)

        if rule_phase and not _phase_matches(state.phase, rule_phase):
            continue

        # missing checks (extend later)
        if missing == "medical_history_checked":
            if state.med_history_asked:
                continue  # not missing
            # else missing -> fire
        # If you later implement options_presented/risks_discussed, you’ll track them in state too.

        prompt = n.get("patient_prompt", "").strip()
        if prompt:
            state.fired_nudges.add(nid)
            return prompt

    return ""