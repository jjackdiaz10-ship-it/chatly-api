# app/services/gemini_service.py
import httpx
import logging
from app.core.config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GOOGLE_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate_response(self, model: str, prompt: str, system_instruction: str = None) -> str:
        """
        Calls the Gemini API using the specified model.
        Model examples: 'gemini-1.5-flash', 'gemini-2.0-flash-exp' (mapped from '2.5 Flash' etc)
        """
        if not self.api_key:
            logger.error("Gemini API Key is missing")
            return "Lo siento, mi conexión con el cerebro de IA está desactivada temporalmente."

        # Map plan names to technical model names
        model_mapping = {
            "Gemini 2.5 Flash": "gemini-2.0-flash-exp", # Using latest experimental/available
            "Gemini 2.0 Flash": "gemini-2.0-flash-exp",
            "Gemini 1.5 Flash": "gemini-1.5-flash"
        }
        
        technical_model = model_mapping.get(model, "gemini-1.5-flash")
        url = f"{self.base_url}/{technical_model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if system_instruction:
            payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=15.0)
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.error(f"Error calling Gemini API: {e}")
                return "Parece que estoy teniendo un momento de reflexión profunda. ¿Puedes repetirme eso?"
