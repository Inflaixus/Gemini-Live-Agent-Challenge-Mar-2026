"""Application-wide constants that do not change at runtime."""

SUPPORTED_RESPONSE_MODALITIES = {"AUDIO", "TEXT"}

RECOMMENDED_NATIVE_AUDIO_MODELS = (
    "gemini-2.5-flash-native-audio-latest",
    "gemini-2.5-flash-native-audio-preview-09-2025",
    "gemini-2.5-flash-native-audio-preview-12-2025",
)

APP_NAME = "bilingual_audio_agent"

# Patterns used to detect leaked meta/process narration in model output.
LEAKY_MODEL_PATTERNS = (
    "searching the patient knowledge base",
    "search_patient_kb",
    "clarifying the ambiguity",
    "acknowledging current state",
    'input "',
    "this is ambiguous",
    "i am currently searching",
    "i'm currently searching",
    "i can confirm, as chloe",
    "as chloe",
    "i'll let you know if the situation improves",
    "i will proceed",
    "i've registered",
    "acknowledge the",
    "assessing the",
    "i need to be direct",
    "improve clarity",
    "struggling to discern",
    "make out any details",
    "need for better illumination",
    "different viewing angle",
    "visibility",
)

VISUAL_UNCLEAR_PATTERNS = (
    "video feed",
    "too dark",
    "dim",
    "unclear",
    "can't see details",
    "cannot see details",
    "unable to give you a clear description",
    "blurry",
    "blurriness",
    "poor lighting",
)
