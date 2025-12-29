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
        from app.models.category import Category
        # 1. Strict Stock Filtering (as requested)
        biz_res = await db.execute(select(Business).where(Business.id == business_id))
        biz = biz_res.scalar_one_or_none()
        
        cat_res = await db.execute(select(Category).where(Category.business_id == business_id))
        categories = cat_res.scalars().all()

        prod_result = await db.execute(
            select(Product).where(
                Product.business_id == business_id, 
                Product.is_active == True,
                Product.stock > 0 # Back to strict stock
            )
        )
        products = prod_result.scalars().all()
        
        return {
            "business": biz,
            "categories": categories,
            "products": products
        }

    async def get_or_create_cart(self, db: AsyncSession, business_id: int, user_phone: str) -> Cart:
        # Include metadata for simple state tracking
        result = await db.execute(
            select(Cart).where(Cart.business_id == business_id, Cart.user_phone == user_phone, Cart.is_active == True)
        )
        cart = result.scalar_one_or_none()
        if not cart:
            cart = Cart(business_id=business_id, user_phone=user_phone)
            db.add(cart)
            await db.flush()
        return cart

    def analyze_semantics(self, message: str) -> Dict[str, float]:
        """
        Ultra-Advanced Semantic Scoring Engine.
        Analyzes every word and assigns scores to possible intents.
        """
        message = message.lower().strip()
        words = re.findall(r'\w+', message)
        
        scores = {
            "greeting": 0.0,
            "catalog": 0.0,
            "checkout": 0.0,
            "view_cart": 0.0,
            "clear_cart": 0.0,
            "help": 0.0
        }
        
        weights = {
            "greeting": ["hola", "buenas", "dias", "tardes", "noches", "hey", "saludos", "inicio"],
            "catalog": ["ver", "catalogo", "productos", "tienda", "comprar", "lista", "inventario", "que", "tienes", "mostrar"],
            "checkout": ["pagar", "listo", "cerrar", "finalizar", "ok", "vale", "confirmar", "link", "pago", "comprar", "adquirir"],
            "view_cart": ["carrito", "pedido", "compras", "tengo", "mi", "ver", "revisar"],
            "clear_cart": ["borrar", "limpiar", "vaciar", "cancelar", "quitar", "eliminar"],
            "help": ["ayuda", "asistencia", "humano", "persona", "soporte"]
        }
        
        for intent, keywords in weights.items():
            for word in words:
                if word in keywords:
                    scores[intent] += 1.3 # Match weight
                # Typo tolerance
                elif len(word) > 3:
                    matches = difflib.get_close_matches(word, keywords, n=1, cutoff=0.8)
                    if matches:
                        scores[intent] += 0.8
        
        return scores

    def get_best_intent(self, scores: Dict[str, float]) -> str:
        max_score = max(scores.values())
        if max_score < 0.5:
            return "general"
        return max(scores, key=scores.get)

    def match_product(self, message: str, products: List[Product]) -> Optional[Product]:
        message = message.lower()
        # Analyze multi-word matches first
        for p in sorted(products, key=lambda x: len(x.name), reverse=True):
            if p.name.lower() in message:
                return p
        # Token-based match
        words = re.findall(r'\w+', message)
        for p in products:
            p_words = p.name.lower().split()
            matches = 0
            for w in words:
                if w in p_words: matches += 1
            if matches >= (len(p_words) / 2) and matches > 0:
                return p
        return None

    async def chat(self, db: AsyncSession, business_id: int, user_phone: str, user_message: str) -> Tuple[Any, str]:
        ctx = await self.get_context(db, business_id)
        products = ctx["products"]
        scores = self.analyze_semantics(user_message)
        intent = self.get_best_intent(scores)
        matched_prod = self.match_product(user_message, products)
        cart = await db.merge(await self.get_or_create_cart(db, business_id, user_phone))

        # VARIATION SYSTEM (To avoid repeating the same responses)
        import random
        greetings = [
            f"¡Hola! Bienvenido a {ctx['business'].name if ctx['business'] else self.business_name}. ¿Cómo puedo asistirte hoy? 🚀",
            f"¡Saludos! Es un gusto saludarte en {self.business_name}. ¿Qué estás buscando hoy?",
            "¡Hola! Soy tu asistente experto. Estoy aquí para ayudarte con tu compra. 😊"
        ]

        # 1. Rules first
        from app.services.rule_engine import RuleEngine
        rule_match = RuleEngine.match(user_message, self.rules)
        if rule_match: return rule_match, "text"

        if intent == "greeting":
            return {
                "type": "button",
                "body": {"text": random.choice(greetings)},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "view_catalog", "title": "Ver Catálogo 🛍️"}},
                        {"type": "reply", "reply": {"id": "view_cart", "title": "Mi Pedido 🛒"}}
                    ]
                }
            }, "interactive"

        if intent == "catalog":
            if not products:
                return "Lo siento, actualmente no tenemos productos con stock disponible. ¡Vuelve pronto!", "text"
            
            rows = []
            for p in products[:10]:
                rows.append({
                    "id": f"prod_{p.id}",
                    "title": p.name[:24],
                    "description": f"${p.price} - Stock: {p.stock}"
                })
            
            return {
                "type": "list",
                "header": {"type": "text", "text": "Catálogo Disponible 🛍️"},
                "body": {"text": "Selecciona un producto para agregarlo a tu pedido:"},
                "footer": {"text": "Solo mostramos productos con stock"},
                "action": {
                    "button": "Ver Productos",
                    "sections": [{"title": "Destacados", "rows": rows}]
                }
            }, "interactive"

        if matched_prod:
            # Check price/info intent vs add intent
            if any(w in user_message.lower() for w in ["quiero", "comprar", "agrega", "pon", "suma", "añadir", "dame"]):
                from sqlalchemy import and_
                item_res = await db.execute(select(CartItem).where(and_(CartItem.cart_id == cart.id, CartItem.product_id == matched_prod.id)))
                item = item_res.scalar_one_or_none()
                if item:
                    item.quantity += 1
                else:
                    db.add(CartItem(cart_id=cart.id, product_id=matched_prod.id))
                await db.commit()
                
                summaries = [
                    f"✅ ¡Excelente elección! He añadido '{matched_prod.name}' a tu pedido.",
                    f"¡Listo! '{matched_prod.name}' ha sido agregado. ¿Quieres algo más?",
                    f"Genial, '{matched_prod.name}' ya está en tu carrito. 🛒"
                ]
                return random.choice(summaries), "text"
            
            return f"El '{matched_prod.name}' está disponible por ${matched_prod.price}. Tenemos {matched_prod.stock} unidades. ¿Te gustaría agregarlo?", "text"

        if intent == "view_cart":
            items_res = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
            items = items_res.scalars().all()
            if not items: return "Tu carrito está vacío. ¿Te gustaría ver nuestro catálogo de hoy? 🛍️", "text"
            
            total = 0
            summary = []
            for item in items:
                p_res = await db.execute(select(Product).where(Product.id == item.product_id))
                p = p_res.scalar_one()
                line = float(p.price) * item.quantity
                total += line
                summary.append(f"• {p.name} x{item.quantity} (${round(line, 2)})")
            
            return {
                "type": "button",
                "body": {"text": f"🛒 *Resumen de tu Pedido:*\n\n" + "\n".join(summary) + f"\n\n💰 *TOTAL: ${round(total, 2)}*"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "checkout", "title": "Finalizar Compra 💳"}},
                        {"type": "reply", "reply": {"id": "clear_cart", "title": "Vaciar Todo 🗑️"}}
                    ]
                }
            }, "interactive"

        if intent == "checkout":
            items_res = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
            items = items_res.scalars().all()
            if not items: return "Para finalizar, primero debes añadir productos. ¿Quieres ver el catálogo?", "text"
            
            total = 0
            for item in items:
                p_res = await db.execute(select(Product).where(Product.id == item.product_id))
                p = p_res.scalar_one()
                total += (float(p.price) * item.quantity)
            
            total = round(total, 2)
            
            # Intelligent step: if they already confirmed or just said "ok/finalizar"
            if any(w in user_message.lower() for w in ["si", "confirmar", "link", "pago", "dame", "enviar"]):
                cart.is_active = False
                await db.commit()
                return f"¡Hecho! 🌟 Tu link de pago por ${total} es:\n\nhttps://pagos.chatly.io/pay/{business_id}?amount={total}&ref={user_phone}\n\n¡Gracias por tu compra!", "text"

            return {
                "type": "button",
                "body": {"text": f"Todo está listo para tu pedido de ${total}. ¿Quieres que te envíe el link de pago ahora?"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "get_link", "title": "Sí, enviar link 💳"}},
                        {"type": "reply", "reply": {"id": "view_catalog", "title": "Seguir viendo �️"}}
                    ]
                }
            }, "interactive"

        if intent == "clear_cart":
            await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
            await db.commit()
            return "Tu carrito ha sido vaciado. ¿En qué más puedo ayudarte? 🧹", "text"

        # General / Fallback with more intelligence
        return f"Entiendo. Estoy analizando tu mensaje... Si buscas productos, escribe 'catálogo'. Si quieres revisar tu compra, escribe 'carrito'. ¿En qué más te puedo ayudar en {self.business_name}?", "text"
