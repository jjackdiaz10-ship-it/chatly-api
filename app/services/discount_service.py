# app/services/discount_service.py
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.cart import Cart, CartItem
from app.models.product import Product
import logging

logger = logging.getLogger(__name__)

class DiscountService:
    """
    Dynamic Discount Engine for Cart Recovery and Sales Optimization.
    Personalizes discount offers based on cart value, customer history, and urgency.
    """
    
    # Tiered discount configuration (can be moved to database later)
    CART_VALUE_TIERS = [
        {"min_value": 200, "code": "VIP20", "percent": 20, "message": "¡Eres cliente VIP!"},
        {"min_value": 100, "code": "PREMIUM15", "percent": 15, "message": "¡Gran compra!"},
        {"min_value": 50, "code": "RECUPERA10", "percent": 10, "message": "¡No te lo pierdas!"},
        {"min_value": 0, "code": "AHORRA5", "percent": 5, "message": "¡Último empujón!"},
    ]
    
    # Time-based urgency multipliers
    URGENCY_BONUSES = {
        2: 5,   # +5% if purchased within 2 hours
        6: 3,   # +3% if purchased within 6 hours
        24: 0,  # No bonus after 24 hours
    }
    
    @staticmethod
    def calculate_cart_total(cart: Cart) -> float:
        """Calculate total cart value."""
        return sum(item.quantity * item.product.price for item in cart.items)
    
    @classmethod
    def calculate_recovery_discount(
        cls,
        cart: Cart,
        urgency_hours: int = 2,
        customer_history: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate personalized discount for abandoned cart recovery.
        
        Args:
            cart: Cart object with items
            urgency_hours: Hours before discount expires (default: 2)
            customer_history: Optional dict with {total_purchases, avg_order_value, is_repeat}
            
        Returns:
            Dict with discount details: {code, percent, min_amount, expires_at, message}
        """
        total = cls.calculate_cart_total(cart)
        
        # 1. Base discount from cart value tiers
        base_discount = None
        for tier in cls.CART_VALUE_TIERS:
            if total >= tier["min_value"]:
                base_discount = tier.copy()
                break
        
        if not base_discount:
            base_discount = cls.CART_VALUE_TIERS[-1].copy()  # Lowest tier
        
        # 2. Add urgency bonus
        urgency_bonus = cls.URGENCY_BONUSES.get(urgency_hours, 0)
        final_percent = base_discount["percent"] + urgency_bonus
        
        # 3. Adjust for customer history (loyalty bonus)
        if customer_history:
            if customer_history.get("is_repeat", False):
                final_percent += 5  # +5% for returning customers
                base_discount["code"] = f"FIEL{int(final_percent)}"
                base_discount["message"] = "¡Gracias por volver!"
        
        # 4. Cap at reasonable maximum
        final_percent = min(final_percent, 30)  # Max 30% discount
        
        # 5. Calculate expiration
        expires_at = datetime.utcnow() + timedelta(hours=urgency_hours)
        
        return {
            "code": base_discount["code"],
            "percent": final_percent,
            "min_amount": base_discount["min_value"],
            "discount_amount": total * (final_percent / 100),
            "final_total": total * (1 - final_percent / 100),
            "expires_at": expires_at,
            "expires_in_hours": urgency_hours,
            "message": base_discount["message"]
        }
    
    @classmethod
    async def get_customer_history(cls, db: AsyncSession, business_id: int, user_phone: str) -> Dict:
        """
        Retrieve customer purchase history for personalization.
        
        Returns:
            Dict with {total_purchases, total_spent, avg_order_value, is_repeat}
        """
        # Count completed purchases
        stmt = select(func.count(Cart.id), func.sum(
            func.coalesce(
                select(func.sum(CartItem.quantity * Product.price))
                .where(CartItem.cart_id == Cart.id)
                .join(Product, CartItem.product_id == Product.id)
                .correlate(Cart)
                .scalar_subquery(),
                0
            )
        )).where(
            Cart.business_id == business_id,
            Cart.user_phone == user_phone,
            Cart.status.in_(["paid", "recovered"])
        )
        
        result = await db.execute(stmt)
        row = result.first()
        
        total_purchases = row[0] if row and row[0] else 0
        total_spent = float(row[1]) if row and row[1] else 0.0
        
        return {
            "total_purchases": total_purchases,
            "total_spent": total_spent,
            "avg_order_value": total_spent / total_purchases if total_purchases > 0 else 0,
            "is_repeat": total_purchases > 0
        }
    
    @classmethod
    async def apply_coupon_to_cart(
        cls,
        db: AsyncSession,
        cart: Cart,
        coupon_code: str
    ) -> Dict:
        """
        Validate and apply coupon code to cart.
        
        Returns:
            Dict with {success, discount_amount, final_total, message}
        """
        # For now, simple validation against known codes
        # TODO: Add Coupon model to database with expiration, usage limits, etc.
        
        known_codes = {tier["code"]: tier["percent"] for tier in cls.CART_VALUE_TIERS}
        
        # Check for VIP/FIEL codes (loyalty)
        if coupon_code.startswith("FIEL"):
            try:
                percent = int(coupon_code.replace("FIEL", ""))
                if 5 <= percent <= 30:
                    known_codes[coupon_code] = percent
            except ValueError:
                pass
        
        if coupon_code not in known_codes:
            return {
                "success": False,
                "message": f"Cupón '{coupon_code}' no válido o expirado."
            }
        
        total = cls.calculate_cart_total(cart)
        percent = known_codes[coupon_code]
        discount_amount = total * (percent / 100)
        final_total = total - discount_amount
        
        # Apply to cart
        cart.coupon_applied = coupon_code
        await db.commit()
        
        logger.info(f"Coupon {coupon_code} applied to cart {cart.id}. Discount: ${discount_amount:.2f}")
        
        return {
            "success": True,
            "coupon_code": coupon_code,
            "percent": percent,
            "discount_amount": discount_amount,
            "original_total": total,
            "final_total": final_total,
            "message": f"✅ ¡Cupón aplicado! Ahorraste ${discount_amount:.0f} ({percent}%)"
        }
    
    @classmethod
    def generate_recovery_message(cls, cart: Cart, discount_info: Dict) -> str:
        """
        Generate persuasive recovery message with discount details.
        
        Args:
            cart: Cart object
            discount_info: Output from calculate_recovery_discount()
            
        Returns:
            Formatted WhatsApp message string
        """
        items_text = ", ".join([
            f"{item.quantity}x {item.product.name}"
            for item in cart.items[:3]  # Show max 3 items
        ])
        
        if len(cart.items) > 3:
            items_text += f" y {len(cart.items) - 3} más"
        
        message = f"🛒 *¡{discount_info['message']}*\n\n"
        message += f"Hola, notamos que dejaste algo especial en tu carrito:\n"
        message += f"📦 {items_text}\n\n"
        
        message += f"💰 *Total original:* ${discount_info['final_total'] / (1 - discount_info['percent']/100):,.0f}\n"
        message += f"🎁 *Con descuento {discount_info['percent']}%:* ${discount_info['final_total']:,.0f}\n"
        message += f"✨ *Ahorras:* ${discount_info['discount_amount']:,.0f}\n\n"
        
        message += f"⏰ *Oferta válida por solo {discount_info['expires_in_hours']} horas.*\n"
        message += f"Usa el cupón *{discount_info['code']}* al finalizar tu compra.\n\n"
        
        message += "👉 ¿Listo para aprovechar esta oferta exclusiva?"
        
        return message
    
    @classmethod
    def generate_checkout_message(cls, cart: Cart, payment_link: str) -> str:
        """
        Generate checkout message with applied discount (if any).
        
        Args:
            cart: Cart object
            payment_link: Payment URL
            
        Returns:
            Formatted message string
        """
        total = cls.calculate_cart_total(cart)
        
        message = "🌟 *¡Excelente selección!*\n\n"
        
        if cart.coupon_applied:
            # Show discount details
            # Try to extract percent from code
            percent = 10  # Default
            for tier in cls.CART_VALUE_TIERS:
                if tier["code"] == cart.coupon_applied:
                    percent = tier["percent"]
                    break
            
            original_total = total / (1 - percent/100)
            discount = original_total - total
            
            message += f"💸 Total original: ${original_total:,.0f}\n"
            message += f"🎁 Descuento ({percent}%): -${discount:,.0f}\n"
            message += f"💰 *Total a pagar: ${total:,.0f}*\n\n"
        else:
            message += f"💰 *Total a pagar: ${total:,.0f}*\n\n"
        
        message += f"🔗 *Completa tu pago aquí:*\n{payment_link}\n\n"
        message += "✅ Pago 100% seguro\n"
        message += "🚀 Procesamiento inmediato\n\n"
        message += "¡Gracias por tu compra! 🙌"
        
        return message
