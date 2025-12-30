# app/services/ai_service.py
import re
import difflib
import json
import logging
import random
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import selectinload
from app.services.gemini_service import GeminiService

# Modelos
from app.models.product import Product
from app.models.cart import Cart, CartItem
from app.models.bot import Bot
from app.models.business import Business
from app.models.category import Category
from app.models.knowledge_base import KnowledgeBase
from app.models.subscription import Subscription
from app.models.plan import Plan

# Configuración de Logging profesional
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class AIService:
    """
    Motor de Ventas Conversacional Mastermind v360 (Vambe-Style).
    Incluye manejo de Base de Conocimientos (FAQs), recuperación y cierre agresivo.
    Dinamizado por el Plan de Suscripción del Negocio.
    """

    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
        self.config = bot.config if bot else {}
        self.business_name = self.config.get("business_name", "Nuestra Tienda")
        self.ai_model = "GPT-3.5-Turbo" # Default
        self.plan_name = "Trial"
        
        # Umbrales de confianza para NLP
        self.CONFIDENCE_THRESHOLD = 0.65
        
        # Motor de IA Generativa
        self.gemini = GeminiService()
        
        # Diccionario de intenciones precompilado
        self.INTENTS = {
            "checkout": ["pagar", "finalizar", "cerrar cuenta", "cobrame", "link de pago", "total", "terminar", "listo", "comprar"],
            "view_cart": ["carrito", "pedido", "mi bolsa", "que llevo", "cuanto voy", "ver compra", "revisar", "cart"],
            "catalog": ["catalogo", "productos", "lista", "que vendes", "menu", "inventario", "ver todo", "tienda", "shop"],
            "add_to_cart": ["quiero", "dame", "agrega", "suma", "llevo", "anadir", "necesito", "pon", "comprar"],
            "greeting": ["hola", "buenas", "hey", "inicio", "empezar", "saludos"],
            "clear_cart": ["vaciar", "borrar todo", "limpiar carrito", "cancelar compra", "resetear"],
            "negative": ["no", "nada", "parar", "basta", "gracias", "no mas", "asi esta bien"],
            "positive": ["si", "dale", "claro", "por supuesto", "perfecto", "bueno", "ok"]
        }

    # --- 1. CORE: GESTIÓN DE DATOS ---

    async def _fetch_plan_config(self, db: AsyncSession, business_id: int):
        """Detecta el plan activo y configura el modelo de IA correspondiente."""
        stmt = (
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.business_id == business_id, Subscription.is_active == True)
        )
        sub = (await db.execute(stmt)).scalar_one_or_none()
        
        if sub and sub.plan:
            self.plan_name = sub.plan.name
            self.ai_model = sub.plan.features.get("ai_model", "Gemini 2.5 Flash")
        else:
            self.plan_name = "Iris Lite"
            self.ai_model = "Gemini 1.5 Flash" # Base model

    async def _get_context_data(self, db: AsyncSession, business_id: int):
        await self._fetch_plan_config(db, business_id)
        biz = await db.scalar(select(Business).where(Business.id == business_id))
        categories = (await db.execute(select(Category).where(Category.business_id == business_id))).scalars().all()
        products = (await db.execute(select(Product).where(Product.business_id == business_id, Product.is_active == True, Product.stock > 0))).scalars().all()
        faqs = (await db.execute(select(KnowledgeBase).where(KnowledgeBase.business_id == business_id))).scalars().all()
        
        return biz, categories, products, faqs

    async def _get_or_create_cart(self, db: AsyncSession, business_id: int, user_phone: str) -> Cart:
        stmt = select(Cart).where(
            Cart.business_id == business_id,
            Cart.user_phone == user_phone,
            Cart.is_active == True
        ).options(selectinload(Cart.items).selectinload(CartItem.product))
        
        cart = (await db.execute(stmt)).scalar_one_or_none()
        if not cart:
            cart = Cart(business_id=business_id, user_phone=user_phone, is_active=True)
            db.add(cart)
            await db.flush()
            cart = (await db.execute(stmt)).scalar_one_or_none()
        
        # Actualizar última interacción
        cart.last_interaction = datetime.utcnow()
        return cart

    # --- 2. MOTOR NLP & CONOCIMIENTO ---

    def _extract_intent(self, message: str) -> str:
        msg = message.lower().strip()
        scores = {k: 0.0 for k in self.INTENTS}
        words = re.findall(r'\w+', msg)
        
        for intent, keywords in self.INTENTS.items():
            for word in words:
                if word in keywords:
                    scores[intent] += 1.2
                elif len(word) > 3:
                    matches = difflib.get_close_matches(word, keywords, n=1, cutoff=0.85)
                    if matches: scores[intent] += 0.8

        best_intent = max(scores, key=scores.get)
        if scores[best_intent] < 0.6: return "search"
        return best_intent

    def _check_faqs(self, message: str, faqs: List[KnowledgeBase]) -> Optional[str]:
        """Búsqueda semántica simple en la base de conocimientos."""
        msg = message.lower()
        best_faq = None
        best_score = 0
        
        for faq in faqs:
            # Score basado en intersección de palabras en la pregunta
            q_words = set(re.findall(r'\w+', faq.question.lower()))
            msg_words = set(re.findall(r'\w+', msg))
            score = len(q_words & msg_words) / len(q_words) if q_words else 0
            
            if score > 0.7 and score > best_score:
                best_score = score
                best_faq = faq
        
        return best_faq.answer if best_faq else None

    # ... (find_product y extract_quantity se mantienen similares) ...
    def _extract_quantity(self, message: str) -> int:
        match = re.search(r'(\d+)\s*(?:de|unidades|uds|u|cajas|items)?', message.lower())
        if match: return min(int(match.group(1)), 99)
        return 1

    def _find_product(self, message: str, products: List[Product]) -> Optional[Product]:
        msg = message.lower()
        if "prod_" in msg:
            try:
                pid = int(re.search(r'prod_(\d+)', msg).group(1))
                return next((p for p in products if p.id == pid), None)
            except: pass
        for p in sorted(products, key=lambda x: len(x.name), reverse=True):
            if p.name.lower() in msg: return p
        msg_tokens = set(re.findall(r'\w+', msg))
        best_match, best_score = None, 0
        for p in products:
            p_tokens = set(re.findall(r'\w+', p.name.lower()))
            score = len(msg_tokens & p_tokens) / len(p_tokens) if p_tokens else 0
            if score > 0.6 and score > best_score: best_score, best_match = score, p
        return best_match

    async def _generate_ai_response(self, user_message: str, products: List[Product], cart: Cart) -> str:
        """Utiliza el modelo de IA del plan para generar una respuesta inteligente."""
        inventory_context = "\n".join([f"- {p.name}: ${p.price}" for p in products[:15]])
        cart_context = ", ".join([f"{i.quantity}x {i.product.name}" for i in cart.items]) if cart.items else "vacío"
        
        system_instruction = f"""
        Eres un Asesor de Ventas Experto de la tienda '{self.business_name}'.
        Tu objetivo es cerrar la venta de forma amable y persuasiva.
        Modelo de IA activo actualmente: {self.ai_model} (Modo: {self.plan_name}).
        
        CONTEXTO ACTUAL:
        - Inventario sugerido: {inventory_context}
        - Carrito del cliente: {cart_context}
        
        REGLAS:
        1. Responde de forma concisa y amigable.
        2. Si el cliente tiene dudas, usa el contexto para ayudarle.
        3. Si no hay productos en el carrito, invita a ver el catálogo.
        4. No menciones que eres una IA a menos que sea necesario.
        """
        
        return await self.gemini.generate_response(
            model=self.ai_model,
            prompt=user_message,
            system_instruction=system_instruction
        )

    # --- 3. ORQUESTADOR ---

    async def chat(self, db: AsyncSession, business_id: int, user_phone: str, user_message: str) -> Tuple[Any, str]:
        try:
            biz, categories, products, faqs = await self._get_context_data(db, business_id)
            cart = await self._get_or_create_cart(db, business_id, user_phone)
            
            # 1. ¿Es una duda frecuente (FAQ)?
            faq_answer = self._check_faqs(user_message, faqs)
            if faq_answer:
                return {
                    "type": "button",
                    "body": {"text": f"💡 *Información Útil:*\n\n{faq_answer}\n\n¿Te gustaría ver nuestra colección ahora?"},
                    "action": {"buttons": [{"type": "reply", "reply": {"id": "catalog", "title": "Ver Catálogo 🛍️"}}]}
                }, "interactive"

            intent = self._extract_intent(user_message)
            matched = self._find_product(user_message, products)
            
            # 2. Manejo de recuperación (si el usuario vuelve tras abandono)
            if cart.status == "abandoned":
                cart.status = "recovered" # Marcar como recuperado al primer contacto
                await db.commit()

            # ... (Lógica de cierre, adición y catálogo refinada) ...
            if intent == "negative" and cart.items:
                return await self._handle_checkout(db, cart, business_id, user_phone)

            if matched and (intent == "add_to_cart" or intent == "search" or user_message.startswith("prod_")):
                return await self._handle_add_to_cart(db, cart, matched, user_message, products)

            if intent == "catalog" or user_message.startswith("cat_"):
                return self._handle_catalog(products, categories, user_message)
            
            elif intent == "view_cart" or (intent == "positive" and cart.items):
                return self._handle_view_cart(cart)
            
            elif intent == "checkout":
                return await self._handle_checkout(db, cart, business_id, user_phone)
            
            elif intent == "clear_cart":
                return await self._handle_clear_cart(db, cart)
                
            elif intent == "greeting":
                return await self._handle_greeting(biz.name if biz else self.business_name)

            return await self._handle_fallback(user_message, products, cart)

        except Exception as e:
            logger.error(f"Error en chat: {e}", exc_info=True)
            return "⚠️ Perdona, tuve un pequeño problema técnico. ¿Podrías intentar de nuevo?", "text"

    # --- 4. HANDLERS (Iguales o mejorados con persuasión) ---

    async def _handle_add_to_cart(self, db, cart, product, message, all_p):
        qty = self._extract_quantity(message)
        if product.stock < qty:
            return f"😅 ¡Lo siento! Solo me quedan {product.stock} unidades de *{product.name}*. ¿Te gustaría llevar esas?", "text"
        item = next((i for i in cart.items if i.product_id == product.id), None)
        if item: item.quantity += qty
        else:
            new_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=qty)
            db.add(new_item)
            cart.items.append(new_item)
        await db.commit()
        total = sum(i.quantity * i.product.price for i in cart.items)
        return {
            "type": "button",
            "body": {"text": f"✅ *¡Añadido!* Su pedido de {product.name} está reservado.\n\n💰 Total: *${total:,.0f}*\n\n¿Necesitas algo más para complementar tu compra?"},
            "action": {"buttons": [{"type": "reply", "reply": {"id": "checkout", "title": "Pagar Ahora 💳"}}, {"type": "reply", "reply": {"id": "catalog", "title": "Seguir Viendo 👀"}}]}
        }, "interactive"

    async def _handle_checkout(self, db, cart, business_id, user_phone):
        if not cart.items: return "🛒 Tu carrito está vacío. ¡Mira nuestro catálogo! 🛍️", "text"
        total = sum(i.quantity * i.product.price for i in cart.items)
        # Link de pago con parámetro de tracking
        payment_link = f"https://pay.chatly.io/{business_id}/{cart.id}?utm=recovery" if cart.status == "recovered" else f"https://pay.chatly.io/{business_id}/{cart.id}"
        cart.is_active = False # Soft close
        await db.commit()
        return f"🌟 *Excelente selección.* He generado tu orden de compra segura.\n\n💰 *Total a pagar: ${total:,.0f}*\n\n🔗 Paga aquí para finalizar: {payment_link}\n\n¡Gracias por preferir {self.business_name}! 🚀", "text"

    def _handle_catalog(self, products, categories, message):
        if message.startswith("cat_"):
            cid = int(message.replace("cat_", ""))
            prods = [p for p in products if p.category_id == cid]
            rows = [{"id": f"prod_{p.id}", "title": p.name[:24], "description": f"${p.price}"} for p in prods[:10]]
            return {"type": "list", "header": {"type": "text", "text": "🎯 Productos"}, "body": {"text": "Toca para agregar:"}, "action": {"button": "Ver", "sections": [{"title": "Opciones", "rows": rows}]}}, "interactive"
        rows = [{"id": f"cat_{c.id}", "title": c.name[:24], "description": "Ver sección"} for c in categories]
        return {"type": "list", "header": {"type": "text", "text": "🛍️ Catálogo"}, "body": {"text": "Elige una categoría:"}, "action": {"button": "Secciones", "sections": [{"title": "Tienda", "rows": rows}]}}, "interactive"

    def _handle_view_cart(self, cart):
        if not cart.items: return "🛒 Carrito vacío. ¿Deseas ver el catálogo?", "text"
        total = sum(i.quantity * i.product.price for i in cart.items)
        return {"type": "button", "body": {"text": f"🧐 *Tu Pedido:* (${total:,.0f})\n\n¿Finalizamos la compra ahora?"}, "action": {"buttons": [{"type": "reply", "reply": {"id": "checkout", "title": "Pagar Ahora 💳"}}, {"type": "reply", "reply": {"id": "clear_cart", "title": "Vaciar 🗑️"}}]}}, "interactive"

    async def _handle_clear_cart(self, db, cart):
        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await db.commit()
        return "🧹 Carrito limpio. ¿Empezamos de nuevo?", "text"

    async def _handle_greeting(self, biz_name):
        model_badge = f" [Powered by {self.ai_model}]" if self.plan_name != "Iris Lite" else ""
        return {
            "type": "button",
            "body": {"text": f"👋 ¡Hola! Bienvenido a *{biz_name}*.\n\nSoy tu asesor comercial 24/7.{model_badge}\n\n¿Cómo puedo ayudarte hoy?"},
            "action": {"buttons": [{"type": "reply", "reply": {"id": "catalog", "title": "Ver Catálogo 🛍️"}}, {"type": "reply", "reply": {"id": "view_cart", "title": "Mi Pedido 🛒"}}]}}, "interactive"

    async def _handle_fallback(self, message, products, cart):
        # En lugar de una respuesta estática, usamos el "Cerebro" del plan
        ai_resp = await self._generate_ai_response(message, products, cart)
        return ai_resp, "text"