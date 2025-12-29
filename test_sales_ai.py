import asyncio
from app.services.ai_service import AIService
from app.db.session import AsyncSessionLocal
from app.models.bot import Bot
from app.models.bot_channel import BotChannel
from app.models.channel import Channel
from app.models.business_channel import BusinessChannel
from app.models.product import Product
import app.models

async def test_ai():
    ai = AIService()
    async with AsyncSessionLocal() as db:
        # Reemplaza '1' con el ID de tu negocio si es diferente
        business_id = 1
        
        test_messages = [
            "Hola, ¿cómo estás?",
            "¿Qué productos tienes?",
            "¿Cuánto cuesta el producto de prueba?",
            "Quiero comprar uno",
            "Adiós"
        ]
        
        print("\n--- TEST NATIVE SALES AI ---\n")
        for msg in test_messages:
            print(f"Cliente: {msg}")
            response = await ai.chat(db, business_id, msg)
            print(f"IA: {response}\n")

if __name__ == "__main__":
    asyncio.run(test_ai())
