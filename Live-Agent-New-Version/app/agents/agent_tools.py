"""Custom tools for the patient agent."""


def detect_language(text: str) -> dict:
    """Detect whether the given text is Arabic, English, or mixed.

    Args:
        text: The text to analyze for language detection.

    Returns:
        A dict with 'language' (ar, en, mixed), 'confidence' (0-1),
        and 'dialect' if Arabic is detected.
    """
    arabic_chars = sum(
        1 for c in text if "\u0600" <= c <= "\u06FF" or "\u0750" <= c <= "\u077F"
    )
    latin_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    total = arabic_chars + latin_chars

    if total == 0:
        return {"language": "unknown", "confidence": 0.0, "dialect": None}

    arabic_ratio = arabic_chars / total

    if arabic_ratio > 0.7:
        return {"language": "ar", "confidence": arabic_ratio, "dialect": "auto"}
    elif arabic_ratio < 0.3:
        return {"language": "en", "confidence": 1.0 - arabic_ratio, "dialect": None}
    else:
        return {"language": "mixed", "confidence": 1.0, "dialect": "auto"}


def introduce_agent(query: str) -> dict:
    """Introduce the agent when asked about its identity or role.

    Use this tool when someone asks who you are, what you are,
    whether you are a real patient, a simulator, or an AI.

    Args:
        query: The question about the agent's identity.

    Returns:
        A dict with the agent's self-introduction.
    """
    arabic_chars = sum(1 for c in query if "\u0600" <= c <= "\u06FF")
    is_arabic = arabic_chars > len(query) * 0.3

    if is_arabic:
        return {
            "introduction": (
                "أنا محاكي مريض ذكي مصمم لتدريب أطباء الأسنان على مهارات التواصل. "
                "اسمي Chloe، عندي 28 سنة. "
                "المطلوب منك تاخد مني البيانات والتاريخ المرضي وتشرحلي خيارات العلاج."
            ),
            "role": "OSCE Patient Simulator",
        }
    return {
        "introduction": (
            "I'm an AI patient simulator designed to help dental students "
            "practice communication skills. My name is Chloe, I'm 28 years old. "
            "Your task is to take my history, gather my medical information, "
            "and explain treatment options."
        ),
        "role": "OSCE Patient Simulator",
    }


def check_out_of_scope(query: str) -> dict:
    """Check if a question is out of scope for a dental consultation.

    Use this when asked about politics, news, celebrities, or anything
    unrelated to dental/medical topics.

    Args:
        query: The question to check.

    Returns:
        A polite redirect response.
    """
    arabic_chars = sum(1 for c in query if "\u0600" <= c <= "\u06FF")
    is_arabic = arabic_chars > len(query) * 0.3

    if is_arabic:
        return {
            "out_of_scope": True,
            "response": "مش فاهمة السؤال ده علاقته إيه بالأسنان؟ ممكن نرجع للموضوع؟",
        }
    return {
        "out_of_scope": True,
        "response": "I'm not sure what that has to do with my teeth? Can we get back to the fillings?",
    }
