import os
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File
from dotenv import load_dotenv

load_dotenv()


class STTService:
    """Service for speech-to-text transcription"""
    
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(os.getenv("STT_MODEL"))
    
    async def transcribe(self, audio_bytes: bytes, mime_type: str) -> str:
        """Transcribe audio to text"""
        response = self.model.generate_content([
            "Transcribe this audio to text.",
            {"mime_type": mime_type, "data": audio_bytes}
        ])
        return response.text


# FastAPI setup
app = FastAPI()
stt_service = STTService()


@app.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    text = await stt_service.transcribe(audio_bytes, audio.content_type)
    return {"text": text}