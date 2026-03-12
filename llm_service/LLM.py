import os
import google.generativeai as genai
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class LLMService:
    """Service for text generation using Gemini LLM"""
    
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(os.getenv("LLM_MODEL"))
    
    def generate(self, prompt: str) -> str:
        """Generate text from prompt"""
        response = self.model.generate_content(prompt)
        return response.text


# FastAPI setup
app = FastAPI()
llm_service = LLMService()


class PromptRequest(BaseModel):
    prompt: str


@app.post("/generate")
def generate_text(data: PromptRequest):
    response = llm_service.generate(data.prompt)
    return {"response": response}