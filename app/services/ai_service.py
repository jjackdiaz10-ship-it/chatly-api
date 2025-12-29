# app/services/ai_service.py
import re
import difflib
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.product import Product
from app.models.cart import Cart, CartItem
from app.models.bot import Bot
from app.models.business import Business
from typing import List, Optional, Dict, Any, Tuple
import logging

class AIService:
    """
    Mastermind Native Sales AI.
    Features: Context-aware, Rule-integrated, Cart-managing, Interactive Suggestion generator.
    """
    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
        self.config = bot.config if bot else {}
        self.rules = bot.rule_set if bot else []
        self.business_name = self.config.get("business_name", "nuestra tienda")

    async def get_context(self, db: AsyncSession, business_id: int) -> Dict[str, Any]:
        result = await db.execute(select(Business).where(Business.id == business_id))
        biz = result.scalar_one_or_none()
        
        prod_result = await db.execute(
            select(Product).where(Product.business_id == business_id, Product.is_active == True)
        )
        products = prod_result.scalars().all()
        
        return {
            "business": biz,
            "products": products
        }

    async def get_or_create_cart(self, db: AsyncSession, business_id: int, user_phone: str) -> Cart:
        result = await db.execute(
            select(Cart).where(Cart.business_id == business_id, Cart.user_phone == user_phone, Cart.is_active == True)
        )
        cart = result.scalar_one_or_none()
        if not cart:
            cart = Cart(business_id=business_id, user_phone=user_phone)
            db.add(cart)
            await db.flush() # Get ID
        return cart

    def detect_intent(self, message: str) -> str:
        message = message.lower().strip()
        if any(word in message for word in ["hola", "buenas", "buenos dias", "tardes", "noches"]): return "greeting"
        if any(word in message for word in ["comprar", "quiero", "pagar", "link", "adquirir", "listo", "cerrar"]): return "checkout"
        if any(word in message for word in ["precio", "cuanto cuesta", "valor", "cuánto", "costo", "vale"]): return "price"
        if any(word in message for word in ["catalogo", "productos", "qué tienes", "lista", "muéstrame"]): return "catalog"
        if any(word in message for word in ["carrito", "qué tengo", "mi pedido", "pedido"]): return "view_cart"
        if any(word in message for word in ["borrar", "limpiar", "vaciar"]): return "clear_cart"
        return "general"

    def match_product(self, message: str, products: List[Product]) -> Optional[Product]:
        message = message.lower()
        # Direct word match
        for p in products:
            if p.name.lower() in message:
                return p
        # Fuzzy match
        product_names = [p.name.lower() for p in products]
        words = message.split()
        for word in words:
            if len(word) < 4: continue
            matches = difflib.get_close_matches(word, product_names, n=1, cutoff=0.7)
            if matches:
                return next(p for p in products if p.name.lower() == matches[0])
        return None

    async def chat(self, db: AsyncSession, business_id: int, user_phone: str, user_message: str) -> Tuple[Any, str]:
        """
        Returns (content, msg_type)
        msg_type can be "text" or "interactive"
        """
        ctx = await self.get_context(db, business_id)
        products = ctx["products"]
        intent = self.detect_intent(user_message)
        matched_prod = self.match_product(user_message, products)
        cart = await self.get_or_create_cart(db, business_id, user_phone)

        # 1. Check Rules First (Mastermind prioritizes defined rules)
        from app.services.rule_engine import RuleEngine
        rule_match = RuleEngine.match(user_message, self.rules)
        if rule_match:
            return rule_match, "text"

        # 2. Intent logic
        if intent == "greeting":
            return {
                "type": "button",
                "body": {"text": f"¡Hola! Bienvenido a {self.business_name}. Soy tu asistente inteligente. ¿Cómo te puedo ayudar hoy?"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "view_catalog", "title": "Ver Catálogo"}},
                        {"type": "reply", "reply": {"id": "view_cart", "title": "Mi Pedido"}}
                    ]
                }
            }, "interactive"

        if intent == "catalog":
            if not products:
                return "Lo siento, no tenemos productos disponibles en este momento.", "text"
            
            rows = []
            for p in products[:10]:
                rows.append({
                    "id": f"prod_{p.id}",
                    "title": p.name[:24],
                    "description": f"${p.price} - {p.description[:60] if p.description else ''}"
                })
            
            return {
                "type": "list",
                "header": {"type": "text", "text": "Catálogo de Productos"},
                "body": {"text": f"Explora lo que tenemos para ti en {self.business_name}:"},
                "footer": {"text": "Toca un producto para verlo"},
                "action": {
                    "button": "Ver Productos",
                    "sections": [{"title": "Destacados", "rows": rows}]
                }
            }, "interactive"

        if matched_prod:
            # Add to cart logic implicitly or ask
            # For robustness, if they mention it with "comprar" or just "quiero", add it
            if any(w in user_message.lower() for w in ["quiero", "comprar", "agrega", "pon"]):
                item_res = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == matched_prod.id))
                item = item_res.scalar_one_or_none()
                if item:
                    item.quantity += 1
                else:
                    db.add(CartItem(cart_id=cart.id, product_id=matched_prod.id))
                await db.commit()
                return f"¡Añadido! He puesto '{matched_prod.name}' en tu carrito. ¿Deseas algo más o quieres finalizar tu compra?", "text"
            
            return f"El '{matched_prod.name}' está disponible por ${matched_prod.price}. ¿Te gustaría agregarlo a tu pedido?", "text"

        if intent == "view_cart":
            # Refresh cart with items
            cart_res = await db.execute(select(Cart).where(Cart.id == cart.id))
            cart = cart_res.scalar_one()
            
            items_res = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
            items = items_res.scalars().all()
            
            if not items:
                return "Tu carrito está vacío. ¿Quieres ver el catálogo?", "text"
            
            total = 0
            summary = []
            for item in items:
                prod_res = await db.execute(select(Product).where(Product.id == item.product_id))
                p = prod_res.scalar_one()
                line_total = p.price * item.quantity
                total += line_total
                summary.append(f"- {p.name} x{item.quantity} (${line_total})")
            
            summary_str = "\n".join(summary)
            return {
                "type": "button",
                "body": {"text": f"Tu Pedido Actual:\n\n{summary_str}\n\n*TOTAL: ${total}*"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "checkout", "title": "Pagar Ahora"}},
                        {"type": "reply", "reply": {"id": "clear_cart", "title": "Vaciar Carrito"}}
                    ]
                }
            }, "interactive"

        if intent == "checkout":
            items_res = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
            items = items_res.scalars().all()
            if not items: return "No tienes productos en tu pedido aún.", "text"
            
            total = 0
            for item in items:
                prod_res = await db.execute(select(Product).where(Product.id == item.product_id))
                p = prod_res.scalar_one()
                total += (p.price * item.quantity)
            
            # Close cart
            cart.is_active = False
            await db.commit()
            
            return f"¡Perfecto! Tu pedido por un total de ${total} ha sido procesado. Aquí tienes el link para finalizar el pago:\n\nhttps://pagos.chatly.io/pay/{business_id}?amount={total}&ref={user_phone}", "text"

        if intent == "clear_cart":
            await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
            await db.commit()
            return "He vaciado tu carrito. ¿En qué más puedo ayudarte?", "text"

        return f"Entiendo. En {self.business_name} estamos para servirte. ¿Quieres ver nuestro catálogo o consultar por algún producto?", "text"
