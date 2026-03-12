import os
import base64
import google.generativeai as genai
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class TTSService:
    """Service for text-to-speech synthesis"""
    
    def __init__(self, voice: str = "en-US"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(os.getenv("TTS_MODEL"))
        self.voice = voice
    
    def synthesize(self, text: str) -> str:
        """Convert text to speech, returns base64 encoded audio"""
        response = self.model.generate_content({
            "text": text,
            "voice": self.voice
        })
        audio_bytes = response.candidates[0].content.parts[0].inline_data.data
        return base64.b64encode(audio_bytes).decode()


# FastAPI setup
app = FastAPI()
tts_service = TTSService()


class TTSRequest(BaseModel):
    text: str


@app.post("/tts")
def text_to_speech(req: TTSRequest):
    audio_base64 = tts_service.synthesize(req.text)
    return {"audio_base64": audio_base64}