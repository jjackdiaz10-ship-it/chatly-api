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
        # 1. Store Knowledge Base
        biz_res = await db.execute(select(Business).where(Business.id == business_id))
        biz = biz_res.scalar_one_or_none()
        
        cat_res = await db.execute(select(Category).where(Category.business_id == business_id))
        categories = cat_res.scalars().all()

        prod_result = await db.execute(
            select(Product).where(
                Product.business_id == business_id, 
                Product.is_active == True,
                Product.stock > 0
            )
        )
        products = prod_result.scalars().all()
        
        return {
            "business": biz,
            "categories": categories,
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
            await db.flush()
        return cart

    def analyze_semantics(self, message: str) -> Dict[str, float]:
        message = message.lower().strip()
        words = re.findall(r'\w+', message)
        
        scores = {
            "greeting": 0.0,
            "catalog": 0.0,
            "category": 0.0,
            "checkout": 0.0,
            "view_cart": 0.0,
            "positive": 0.0,
            "negative": 0.0
        }
        
        weights = {
            "greeting": ["hola", "buenas", "hey", "inicio", "saludos"],
            "catalog": ["ver", "catalogo", "productos", "tienda", "comprar", "lista", "inventario"],
            "category": ["categoria", "seccion", "tipo", "clase", "rubro"],
            "checkout": ["pagar", "finalizar", "listo", "cerrar", "pago", "total", "checkout", "terminar"],
            "view_cart": ["carrito", "pedido", "compra", "tengo", "mi", "bolsa"],
            "positive": ["si", "dale", "claro", "agrega", "pon", "quiero", "perfecto", "bueno", "ok"],
            "negative": ["no", "nada", "asi", "bien", "basta", "gracias", "ningun", "parar"]
        }
        
        for intent, keywords in weights.items():
            for word in words:
                if word in keywords: scores[intent] += 1.5
                elif len(word) > 3:
                    matches = difflib.get_close_matches(word, keywords, n=1, cutoff=0.85)
                    if matches: scores[intent] += 1.0
        
        return scores

    async def get_related(self, db: AsyncSession, p: Product, all_p: List[Product]) -> Optional[Product]:
        related = [x for x in all_p if x.category_id == p.category_id and x.id != p.id]
        return random.choice(related) if related else None

    async def chat(self, db: AsyncSession, business_id: int, user_phone: str, user_message: str) -> Tuple[Any, str]:
        import random
        ctx = await self.get_context(db, business_id)
        products = ctx["products"]
        categories = ctx["categories"]
        scores = self.analyze_semantics(user_message)
        intent = max(scores, key=scores.get) if max(scores.values()) > 0.8 else "general"
        cart = await db.merge(await self.get_or_create_cart(db, business_id, user_phone))
        meta = json.loads(cart.metadata_json or "{}")

        # Load Items
        items_res = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
        items = items_res.scalars().all()

        # PERSISTENT STATE MACHINE LOGIC
        # 1. Check if user clicked a Product from List or mentioned it
        matched_prod = None
        # Check if message is a Product ID from List (e.g., "prod_5")
        if user_message.startswith("prod_"):
            try:
                pid = int(user_message.replace("prod_", ""))
                matched_prod = next((p for p in products if p.id == pid), None)
            except: pass
        
        if not matched_prod:
            # Fuzzy match in names
            for p in sorted(products, key=lambda x: len(x.name), reverse=True):
                if p.name.lower() in user_message.lower():
                    matched_prod = p
                    break

        # ACTION: ADD TO CART (Professional Flow)
        if matched_prod and any(w in user_message.lower() for w in ["quiero", "comprar", "agrega", "vende", "pon", "da", "añadir", "dame", "prod_"]):
            from sqlalchemy import and_
            item_res = await db.execute(select(CartItem).where(and_(CartItem.cart_id == cart.id, CartItem.product_id == matched_prod.id)))
            item = item_res.scalar_one_or_none()
            if item: item.quantity += 1
            else: db.add(CartItem(cart_id=cart.id, product_id=matched_prod.id))
            
            # Update state for follow-up
            meta["last_prod_id"] = matched_prod.id
            cart.metadata_json = json.dumps(meta)
            await db.commit()
            
            # Suggest Upsell
            rel = await self.get_related(db, matched_prod, products)
            msg = f"✅ *¡Excelente elección!* He añadido '{matched_prod.name}' a tu pedido.\n\n"
            if rel:
                msg += f"💡 *Recomendación Experta:* Muchos clientes también llevan el '{rel.name}' por solo ${rel.price}. ¿Te gustaría que lo agregue también?\n\n"
            
            return {
                "type": "button",
                "body": {"text": msg + "¿Deseas algo más o quieres finalizar tu compra ahora?"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "view_catalog", "title": "Ver más 🏙️"}},
                        {"type": "reply", "reply": {"id": "checkout", "title": "Pagar Ahora 💳"}}
                    ]
                }
            }, "interactive"

        # ACTION: CATEGORY SELECTION
        if user_message.startswith("cat_"):
            cid = int(user_message.replace("cat_", ""))
            cat_prods = [p for p in products if p.category_id == cid]
            if not cat_prods: return "Esta sección está vacía por ahora. 😊", "text"
            
            rows = [{"id": f"prod_{p.id}", "title": p.name[:24], "description": f"${p.price} - Stock: {p.stock}"} for p in cat_prods[:10]]
            return {
                "type": "list",
                "header": {"type": "text", "text": "Sección Seleccionada 📍"},
                "body": {"text": "Toca el producto que desees para agregarlo:"},
                "footer": {"text": "Precios con IVA incluido"},
                "action": {
                    "button": "Ver Productos",
                    "sections": [{"title": "Disponibles", "rows": rows}]
                }
            }, "interactive"

        # INTENTS
        if intent == "greeting":
            return {
                "type": "button",
                "body": {"text": f"¡Hola! Bienvenido a *{ctx['business'].name if ctx['business'] else self.business_name}*. 🚀\n\nSoy tu asesor comercial inteligente. ¿Cómo te puedo ayudar hoy?"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "view_catalog", "title": "Explorar Tienda �"}},
                        {"type": "reply", "reply": {"id": "checkout", "title": "Finalizar Pedido �"}}
                    ]
                }
            }, "interactive"

        if intent == "catalog":
            if len(categories) > 1:
                rows = [{"id": f"cat_{c.id}", "title": c.name[:24], "description": "Ver productos de esta sección"} for c in categories]
                return {
                    "type": "list",
                    "header": {"type": "text", "text": "Catálogo General 🛍️"},
                    "body": {"text": "Para tu comodidad, he dividido la tienda por categorías. ¿Cuál deseas explorar?"},
                    "footer": {"text": "Chatly Sales AI"},
                    "action": {
                        "button": "Seleccionar Categoría",
                        "sections": [{"title": "Categorías", "rows": rows}]
                    }
                }, "interactive"
            else:
                rows = [{"id": f"prod_{p.id}", "title": p.name[:24], "description": f"${p.price} - Stock: {p.stock}"} for p in products[:10]]
                return {
                    "type": "list",
                    "header": {"type": "text", "text": "Nuestra Vitrina 💎"},
                    "body": {"text": "Toca un producto para añadirlo de inmediato:"},
                    "action": {
                        "button": "Ver Productos",
                        "sections": [{"title": "Disponibles", "rows": rows}]
                    }
                }, "interactive"

        if intent == "view_cart":
            if not items: return "Tu carrito está esperando por su primera compra. 😊 ¿Vemos el catálogo?", "text"
            total = sum(float(i.product.price) * i.quantity for i in items)
            summary = "\n".join([f"• {i.product.name} x{i.quantity} (${round(float(i.product.price)*i.quantity, 2)})" for i in items])
            return {
                "type": "button",
                "body": {"text": f"�️ *Resumen de tu Pedido:*\n\n{summary}\n\n� *TOTAL: ${round(total, 2)}*"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "checkout", "title": "Pagar Ahora 💳"}},
                        {"type": "reply", "reply": {"id": "view_catalog", "title": "Seguir Comprando 🛍️"}}
                    ]
                }
            }, "interactive"

        # CLOSING LOGIC (Conversion Focus)
        if intent == "checkout" or (intent == "negative" and items):
            total = sum(float(i.product.price) * i.quantity for i in items)
            if total <= 0: return "Tu pedido está vacío. 🛒 ¿Te muestro el catálogo?", "text"
            
            # If user confirms or said No thanks (closing time)
            if any(w in user_message.lower() for w in ["si", "dale", "ok", "pago", "link", "gracias", "listo", "cerrar", "finalizar", "nada"]):
                cart.is_active = False
                await db.commit()
                return f"🔥 *¡Trato hecho!* 🔥\n\nTu pedido por *${round(total, 2)}* ha sido reservado.\n\nPaga de forma segura aquí: https://pagos.chatly.io/pay/{business_id}?amount={total}&ref={user_phone}\n\nEn cuanto recibamos el pago, procesaremos tu envío. ¡Gracias por confiar en {self.business_name}!", "text"

            return {
                "type": "button",
                "body": {"text": f"¡Excelente decisión! Tienes una compra espectacular por *${round(total, 2)}*.\n\n¿Generamos el link de pago ahora mismo para asegurar tu stock antes de que se agote?"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "paid_link", "title": "Sí, enviar link 💳"}},
                        {"type": "reply", "reply": {"id": "view_catalog", "title": "Ver más 🛍️"}}
                    ]
                }
            }, "interactive"

        if matched_prod:
            return f"¡Buena elección! El '{matched_prod.name}' tiene un valor de ${matched_prod.price} y nos quedan {matched_prod.stock} unidades. ¿Te gustaría agregarlo a tu pedido ahora mismo? ✅", "text"

        if intent == "clear_cart":
            await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
            await db.commit()
            return "Carrito vaciado con éxito. 🗑️ ¿Deseas empezar de nuevo?", "text"

        return f"Entiendo perfectamente. En {self.business_name} estamos para asesorarte. 🚀 ¿Deseas ver el catálogo o prefieres revisar tu pedido actual?", "text"
