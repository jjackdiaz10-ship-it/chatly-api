# app/services/ai_service.py
import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product import Product
from app.models.business import Business
from typing import List, Optional
import os

class AIService:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def get_business_context(self, db: AsyncSession, business_id: int) -> str:
        # Fetch products for the business
        result = await db.execute(
            select(Product).where(Product.business_id == business_id, Product.is_active == True)
        )
        products = result.scalars().all()
        
        context = "Eres un asistente de ventas humano, amable y muy enfocado en cerrar la venta de forma rápida.\n"
        context += "Tu objetivo es ayudar al cliente a decidirse y concretar el pago de inmediato.\n"
        context += "Reglas de oro:\n"
        context += "1. RESPUESTAS MUY CORTAS: Máximo 2 oraciones. Sé directo pero amable.\n"
        context += "2. PRODUCTO EXACTO: Si el cliente pregunta por algo, menciónalo y da el precio.\n"
        context += "3. CIERRE DE VENTA: Si el cliente parece interesado, di algo como '¡Excelente elección! Te paso el link para que puedas pagarlo ahora mismo' seguido del placeholder [PAYLINK:ID_DEL_PRODUCTO] (reemplaza ID_DEL_PRODUCTO con el ID numérico).\n"
        context += "4. LENGUAJE NATURAL: Habla como una persona real, evita sonar como un bot rígido.\n\n"
        context += "Productos disponibles:\n"
        
        for p in products:
            context += f"- ID: {p.id}, {p.name} (${p.price}): {p.description}\n"
            
        return context

    async def chat(self, db: AsyncSession, business_id: int, user_message: str, chat_history: List[dict] = []) -> str:
        context = await self.get_business_context(db, business_id)
        
        # Build the prompt
        full_prompt = f"{context}\n\nCliente: {user_message}\nAsistente (Conciso y enfocado en venta):"
        
        # In a real scenario, we would inject the payment link generation capability 
        # or use function calling. For simplicity, we'll let the AI use the link placeholder
        # and we can post-process or just ensure it knows to use the placeholder.
        
        response = await self.model.generate_content_async(full_prompt)
        return response.text
