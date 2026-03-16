import re

OUT_OF_SCOPE_REPLY = "I can only role-play the patient in the provided dental scenarios. I can’t help with that."

def detect_smalltalk_intents(text: str) -> set[str]:
    t = text.lower()
    intents = set()
    if re.search(r"\b(hi|hello|hey|good morning|good evening)\b", t):
        intents.add("greet")
    if re.search(r"\b(thank you|thanks|appreciate)\b", t):
        intents.add("thanks")
    if re.search(r"\b(congrats|congratulations|mabrouk)\b", t):
        intents.add("congrats")
    if re.search(r"\b(bye|goodbye|see you|talk later)\b", t):
        intents.add("bye")
    return intents

def smalltalk_reply(intents: set[str]) -> str:
    parts = []
    if "greet" in intents: parts.append("Hello.")
    if "thanks" in intents: parts.append("Thanks.")
    if "congrats" in intents: parts.append("Congratulations.")
    if "bye" in intents: parts.append("Okay, goodbye.")
    return " ".join(parts)

def is_out_of_scope(text: str) -> bool:
    """
    Detect truly unrelated topics (not dental/medical consultation).
    Be conservative: only block clearly irrelevant topics.
    """
    t = text.lower()
    
    # Hard block: completely unrelated domains
    blocked_domains = [
        "weather", "forecast", "temperature", "rain", "snow",
        "politics", "election", "president", "government", "vote",
        "bitcoin", "crypto", "stock", "investment", "trading",
        "sports score", "football match", "game result",
        "movie", "film", "tv show", "netflix","fiancé","eat"
        "recipe", "cooking", "restaurant recommendation"
    ]
    
    # Check if message is asking for information (not just mentioning)
    asking_patterns = ["what is", "what's", "tell me about", "how is", "who won", "when is"]
    is_asking = any(p in t for p in asking_patterns)
    
    if is_asking:
        return any(b in t for b in blocked_domains)
    
    # If just mentioning (not asking), be more lenient
    return False

def looks_like_dental_osce(text: str) -> bool:
    t = text.lower()
    cues = ["tooth", "teeth", "filling", "amalgam", "dent", "whitening", "smile", "pain", "sensitivity", "gum"]
    return any(c in t for c in cues)

def looks_like_consultation_dialogue(text: str) -> bool:
    t = text.lower()
    cues = [
        "i don't understand", "i dont understand", "what do you mean",
        "can you explain", "pros and cons", "advantages", "disadvantages",
        "downside", "benefit", "risk", "is it safe", "what happens if",
        "how long", "how many visits", "how much", "cost", "price",
        "okay", "got it", "makes sense"
    ]
    return any(c in t for c in cues)


SELF_INTRO_REPLY = (
    "We are developing a Live AI Agent... that simulates a dental patient encounter. "
    "The goal is to help postgraduate dentists prepare for fellowship and clinical examinations. "
    "So basically... the system allows dentists to practice things like history taking, "
    "patient assessment, clinical decision-making, consultation, and diagnosis... "
    "all in a realistic, exam-like scenario. "
    "This interactive training environment... helps clinicians strengthen their clinical reasoning, "
    "and their communication skills... before their actual exams."
)


def is_self_intro_question(text: str) -> bool:
    """Detect if the user is asking the agent to introduce itself."""
    t = text.lower()
    patterns = [
        "who are you", "introduce yourself", "what are you",
        "tell me about yourself",
         "what is this",
    ]
    return any(p in t for p in patterns)
