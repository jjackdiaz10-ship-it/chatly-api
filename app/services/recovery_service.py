# app/services/recovery_service.py
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.models.cart import Cart, CartItem
from app.services.meta_service import MetaService
from app.models.business_channel import BusinessChannel

logger = logging.getLogger(__name__)

class RecoveryService:
    """
    Automates abandoned cart recovery via WhatsApp.
    Scans for carts without activity for > 1 hour.
    """
    
    @staticmethod
    async def scan_and_recover(db):
        now = datetime.utcnow()
        threshold = now - timedelta(hours=1)
        
        # 1. Identificar carritos abandonados (activos, última interacción > 1h, no notificados recientemente)
        stmt = select(Cart).where(
            Cart.is_active == True,
            Cart.status == "active",
            Cart.last_interaction < threshold,
            (Cart.last_notified_at == None) | (Cart.last_notified_at < now - timedelta(hours=24))
        ).options(selectinload(Cart.items).selectinload(CartItem.product))
        
        result = await db.execute(stmt)
        abandoned_carts = result.scalars().all()
        
        for cart in abandoned_carts:
            if not cart.items: continue
            
            try:
                # 2. Obtener canal de WhatsApp del negocio
                chan_stmt = select(BusinessChannel).where(
                    BusinessChannel.business_id == cart.business_id,
                    BusinessChannel.channel_type == "WHATSAPP"
                )
                chan = (await db.execute(chan_stmt)).scalar_one_or_none()
                
                if not chan or not chan.token:
                    continue
                
                # 3. Preparar mensaje de recuperación persuasivo con descuento dinámico
                from app.services.discount_service import DiscountService
                
                # Get customer history for personalization
                customer_history = await DiscountService.get_customer_history(db, cart.business_id, cart.user_phone)
                
                # Calculate personalized discount
                discount_info = DiscountService.calculate_recovery_discount(
                    cart=cart,
                    urgency_hours=2,
                    customer_history=customer_history
                )
                
                # Generate persuasive message
                message = DiscountService.generate_recovery_message(cart, discount_info)
                
                # 4. Enviar vía MetaService
                meta = MetaService(chan.token, chan.provider_id)
                await meta.send_whatsapp_message(cart.user_phone, message)
                
                # 5. Marcar como notificado
                cart.last_notified_at = now
                cart.status = "abandoned"
                await db.commit()
                logger.info(f"Recovery message sent to {cart.user_phone} for business {cart.business_id}")
                
            except Exception as e:
                logger.error(f"Error recovering cart {cart.id}: {e}")
                
        return len(abandoned_carts)
