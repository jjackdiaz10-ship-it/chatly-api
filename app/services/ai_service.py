# app/services/ai_service.py
import re
import difflib
import json
import logging
import random
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import selectinload

# Modelos
from app.models.product import Product
from app.models.cart import Cart, CartItem
from app.models.bot import Bot
from app.models.business import Business
from app.models.category import Category

# Configuración de Logging profesional
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class AIService:
    """
    Motor de Ventas Conversacional Mastermind v3.0 (Hybrid High-Performance).
    Combina una arquitectura modular con lógica de cierre de alto impacto y persistencia robusta.
    """

    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
        self.config = bot.config if bot else {}
        self.business_name = self.config.get("business_name", "Nuestra Tienda")
        
        # Umbrales de confianza para NLP
        self.CONFIDENCE_THRESHOLD = 0.65
        
        # Diccionario de intenciones precompilado
        self.INTENTS = {
            "checkout": ["pagar", "finalizar", "cerrar cuenta", "cobrame", "link de pago", "total", "terminar", "check out", "listo"],
            "view_cart": ["carrito", "pedido", "mi bolsa", "que llevo", "cuanto voy", "ver compra", "revisar"],
            "catalog": ["catalogo", "productos", "lista", "que vendes", "menu", "inventario", "ver todo", "tienda"],
            "add_to_cart": ["quiero", "dame", "agrega", "suma", "llevo", "anadir", "necesito", "comprar", "pon"],
            "greeting": ["hola", "buenas", "hey", "inicio", "empezar", "saludos"],
            "clear_cart": ["vaciar", "borrar todo", "limpiar carrito", "cancelar compra", "resetear"],
            "negative": ["no", "nada", "parar", "basta", "gracias", "no mas", "asi esta bien"],
            "positive": ["si", "dale", "claro", "por supuesto", "perfecto", "bueno", "ok"]
        }

    # --- 1. CORE: GESTIÓN DE DATOS ---

    async def _get_context_data(self, db: AsyncSession, business_id: int):
        """Carga optimizada de datos en una sola transacción."""
        biz = await db.scalar(select(Business).where(Business.id == business_id))
        categories = (await db.execute(select(Category).where(Category.business_id == business_id))).scalars().all()
        
        products = (await db.execute(
            select(Product).where(
                Product.business_id == business_id,
                Product.is_active == True,
                Product.stock > 0
            )
        )).scalars().all()
        
        return biz, categories, products

    async def _get_or_create_cart(self, db: AsyncSession, business_id: int, user_phone: str) -> Cart:
        """Obtiene el carrito con carga anticipada (selectinload) para evitar bugs de 'carrito vacío'."""
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
            
        return cart

    # --- 2. MOTOR NLP (INTELIGENCIA) ---

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
        if scores[best_intent] < 0.6:
            return "search"
            
        return best_intent

    def _extract_quantity(self, message: str) -> int:
        patterns = [
            r'(\d+)\s*(?:de|unidades|uds|u|cajas|items)',
            r'(?:quiero|dame|pon|agrega|x)\s*(\d+)',
            r'^(\d+)$'
        ]
        for p in patterns:
            match = re.search(p, message.lower())
            if match:
                try:
                    return min(int(match.group(1)), 99)
                except ValueError: continue
        return 1

    def _find_product(self, message: str, products: List[Product]) -> Optional[Product]:
        msg = message.lower()
        if "prod_" in msg:
            try:
                pid = int(re.search(r'prod_(\d+)', msg).group(1))
                return next((p for p in products if p.id == pid), None)
            except: pass

        # Coincidencia de frase exacta (prioridad nombres largos)
        for p in sorted(products, key=lambda x: len(x.name), reverse=True):
            if p.name.lower() in msg: return p
        
        # Intersección de tokens
        msg_tokens = set(re.findall(r'\w+', msg))
        best_match, best_score = None, 0
        for p in products:
            p_tokens = set(re.findall(r'\w+', p.name.lower()))
            score = len(msg_tokens & p_tokens) / len(p_tokens) if p_tokens else 0
            if score > 0.6 and score > best_score:
                best_score, best_match = score, p
                
        return best_match

    # --- 3. ORQUESTADOR ---

    async def chat(self, db: AsyncSession, business_id: int, user_phone: str, user_message: str) -> Tuple[Any, str]:
        try:
            biz, categories, products = await self._get_context_data(db, business_id)
            cart = await self._get_or_create_cart(db, business_id, user_phone)
            intent = self._extract_intent(user_message)
            matched = self._find_product(user_message, products)
            
            # Cierre inteligente: Si dice "no" o "nada más" y tiene cosas, vamos a checkout
            if intent == "negative" and cart.items:
                return await self._handle_checkout(db, cart, business_id, user_phone)

            # Lógica de adición
            if matched and (intent == "add_to_cart" or intent == "search" or user_message.startswith("prod_")):
                return await self._handle_add_to_cart(db, cart, matched, user_message, products)

            # Enrutamiento modular
            if intent == "catalog" or user_message.startswith("cat_"):
                return self._handle_catalog(products, categories, user_message)
            
            elif intent == "view_cart" or (intent == "positive" and cart.items):
                return self._handle_view_cart(cart)
            
            elif intent == "checkout":
                return await self._handle_checkout(db, cart, business_id, user_phone)
            
            elif intent == "clear_cart":
                return await self._handle_clear_cart(db, cart)
                
            elif intent == "greeting":
                return self._handle_greeting(biz.name if biz else self.business_name)

            # Fallback Persuasivo
            return self._handle_fallback(user_message, products, cart)

        except Exception as e:
            logger.error(f"Error en chat: {e}", exc_info=True)
            return "⚠️ Perdona, tuve un pequeño problema técnico. ¿Podrías intentar de nuevo o escribir 'inicio'?", "text"

    # --- 4. HANDLERS ---

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

        # Cross-selling (Upsell)
        rel_p = [p for p in all_p if p.category_id == product.category_id and p.id != product.id]
        upsell_text = ""
        if rel_p:
            u = random.choice(rel_p)
            upsell_text = f"\n💡 *Sugerencia:* Muchos clientes también llevan el *{u.name}* (${u.price})."

        total = sum(i.quantity * i.product.price for i in cart.items)
        return {
            "type": "button",
            "body": {
                "text": f"✅ *¡Añadido!* He sumado {qty}x {product.name} a tu pedido.\n\n"
                        f"� Total hasta ahora: *${total:,.0f}*{upsell_text}\n\n"
                        "¿Quieres ver algo más o prefieres pagar ahora?"
            },
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "checkout", "title": "Pagar Ahora 💳"}},
                    {"type": "reply", "reply": {"id": "catalog", "title": "Ver Catálogo �️"}}
                ]
            }
        }, "interactive"

    def _handle_catalog(self, products, categories, message):
        if message.startswith("cat_"):
            cid = int(message.replace("cat_", ""))
            prods = [p for p in products if p.category_id == cid]
            if not prods: return "Esta sección está vacía por ahora. 🌟", "text"
            
            rows = [{"id": f"prod_{p.id}", "title": p.name[:24], "description": f"${p.price} | Stock: {p.stock}"} for p in prods[:10]]
            return {
                "type": "list",
                "header": {"type": "text", "text": "🎯 Catálogo Especial"},
                "body": {"text": "Toca un producto para añadirlo a tu compra:"},
                "action": {"button": "Ver Productos", "sections": [{"title": "Disponibles", "rows": rows}]}
            }, "interactive"

        rows = [{"id": f"cat_{c.id}", "title": c.name[:24], "description": "Ver productos"} for c in categories]
        return {
            "type": "list",
            "header": {"type": "text", "text": "�️ Nuestra Tienda"},
            "body": {"text": "He organizado todo por categorías para tu comodidad. ¿Cuál deseas explorar?"},
            "action": {"button": "Abrir Secciones", "sections": [{"title": "Categorías", "rows": rows}]}
        }, "interactive"

    async def _handle_checkout(self, db, cart, business_id, user_phone):
        if not cart.items:
            return "🛒 Tu carrito está vacío. ¡Mira nuestro catálogo para empezar! 🛍️", "text"
        
        total = sum(i.quantity * i.product.price for i in cart.items)
        summary = "\n".join([f"▪ {i.quantity}x {i.product.name} (${i.quantity*i.product.price:,.0f})" for i in cart.items])
        
        # El link se envía en el BODY como texto, ya que 'url' no es un botón interactive estándar soportado globalmente en este flujo.
        payment_link = f"https://pagos.chatly.io/pay/{business_id}?amount={total}&ref={user_phone}"
        
        # Marcamos como inactivo para que la próxima compra sea un carrito nuevo
        cart.is_active = False
        await db.commit()

        return f"🌟 *¡Excelente elección!* Tu pedido está listo.\n\n" \
               f"� *Resumen:*\n{summary}\n\n" \
               f"💰 *Total Final: ${total:,.0f}*\n\n" \
               f"Paga aquí de forma segura para procesar tu envío: {payment_link}\n\n" \
               f"¡Gracias por confiar en {self.business_name}! �", "text"

    def _handle_view_cart(self, cart):
        if not cart.items:
            return "🛒 Tu carrito está esperando su primer producto. ¿Vemos el catálogo?", "text"
        
        items_desc = "\n".join([f"• {i.quantity}x {i.product.name} (${i.quantity*i.product.price:,.0f})" for i in cart.items])
        total = sum(i.quantity * i.product.price for i in cart.items)
        
        return {
            "type": "button",
            "body": {"text": f"🧐 *Tu Pedido Actual:*\n\n{items_desc}\n\n💰 *Total: ${total:,.0f}*"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "checkout", "title": "Pagar Ahora 💳"}},
                    {"type": "reply", "reply": {"id": "clear_cart", "title": "Vaciar Carrito 🗑️"}}
                ]
            }
        }, "interactive"

    async def _handle_clear_cart(self, db, cart):
        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await db.commit()
        return "🧹 Carrito vaciado con éxito. ¿Deseas empezar de nuevo?", "text"

    def _handle_greeting(self, biz_name):
        return {
            "type": "button",
            "body": {"text": f"👋 ¡Hola! Bienvenido a *{biz_name}*.\n\nSoy tu asesor comercial inteligente. ¿Deseas ver nuestra colección o revisar algo que ya tengas en mente?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "catalog", "title": "Ver Catálogo 🛍️"}},
                    {"type": "reply", "reply": {"id": "view_cart", "title": "Mi Pedido 🛒"}}
                ]
            }
        }, "interactive"

    def _handle_fallback(self, message, products, cart):
        if cart.items:
            total = sum(i.quantity * i.product.price for i in cart.items)
            return {
                "type": "button",
                "body": {"text": f"📍 *Nota:* No estoy seguro de haber entendido eso, pero veo que tienes un pedido por *${total:,.0f}* pendiente.\n\n¿Deseas finalizar el pago o seguir explorando?"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "checkout", "title": "Pagar Ahora 💳"}},
                        {"type": "reply", "reply": {"id": "catalog", "title": "Ver Catálogo 🛍️"}}
                    ]
                }
            }, "interactive"

        return {
            "type": "button",
            "body": {"text": "🤔 No logré captar eso último. ¿Te gustaría ver nuestro catálogo oficial o prefieres que un humano te ayude?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "catalog", "title": "Ver Catálogo 🛍️"}},
                    {"type": "reply", "reply": {"id": "help", "title": "Hablar con alguien �"}}
                ]
            }
        }, "interactive"