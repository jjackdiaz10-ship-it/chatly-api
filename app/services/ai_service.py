# app/services/ai_service.py
import re
import difflib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product import Product
from typing import List, Optional, Dict, Any
import logging

class AIService:
    """
    Native Sales AI that uses pure Python logic (Regex + Fuzzy Matching)
    to provide a robust, free, and efficient sales experience.
    """
    def __init__(self, api_key: Optional[str] = None):
        # We ignore api_key as this is now a native implementation
        pass

    async def get_active_products(self, db: AsyncSession, business_id: int) -> List[Product]:
        result = await db.execute(
            select(Product).where(Product.business_id == business_id, Product.is_active == True)
        )
        return result.scalars().all()

    def detect_intent(self, message: str) -> str:
        message = message.lower().strip()
        
        if any(word in message for word in ["hola", "buenas", "buenos dias", "buentas tardes", "buenas noches"]):
            return "greeting"
        if any(word in message for word in ["comprar", "quiero", "pagar", "link", "adquirir"]):
            return "buy"
        if any(word in message for word in ["precio", "cuanto cuesta", "valor", "cuánto", "costo", "vale"]):
            return "price"
        if any(word in message for word in ["catalogo", "productos", "qué tienes", "lista", "muéstrame"]):
            return "catalog"
        
        return "general"

    def match_product(self, message: str, products: List[Product]) -> Optional[Product]:
        product_names = [p.name.lower() for p in products]
        # Try to find close matches for individual words or the whole phrase
        words = message.lower().split()
        potential_matches = []
        
        for name in product_names:
            if name in message.lower():
                potential_matches.append(name)
        
        if not potential_matches:
            # Use fuzzy matching if no direct mention
            for word in words:
                matches = difflib.get_close_matches(word, product_names, n=1, cutoff=0.6)
                if matches:
                    potential_matches.append(matches[0])
        
        if potential_matches:
            # Return the first high-confidence match
            for p in products:
                if p.name.lower() == potential_matches[0]:
                    return p
        return None

    async def chat(self, db: AsyncSession, business_id: int, user_message: str, chat_history: List[dict] = []) -> str:
        print(f"DEBUG: Processing native AI chat for business {business_id} - Msg: {user_message}")
        
        products = await self.get_active_products(db, business_id)
        intent = self.detect_intent(user_message)
        matched_prod = self.match_product(user_message, products)
        
        if intent == "greeting":
            return "¡Hola! Soy tu asistente de ventas. ¿En qué puedo ayudarte hoy? Tenemos productos increíbles para ti."
            
        if intent == "catalog":
            if not products:
                return "Por ahora no tenemos productos disponibles, pero pronto tendremos novedades."
            prod_list = ", ".join([f"{p.name} (${p.price})" for p in products[:5]])
            return f"Claro, tenemos: {prod_list}. ¿Alguno te interesa?"

        if matched_prod:
            if intent == "buy":
                return f"¡Excelente elección! El {matched_prod.name} es genial. Te paso el link para que puedas pagarlo ahora mismo: [PAYLINK:{matched_prod.id}]"
            else:
                return f"El {matched_prod.name} tiene un precio de ${matched_prod.price}. ¿Te gustaría comprarlo?"

        if intent == "price" or intent == "buy":
            if products:
                return f"¿Sobre qué producto te gustaría consultar? Tenemos {products[0].name} y más."
            return "Dime qué producto te interesa y te daré el precio."

        # Default robust response
        return "Entiendo. ¿Te gustaría conocer nuestros productos o tienes alguna duda específica sobre una compra?"
