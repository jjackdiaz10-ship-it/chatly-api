# app/api/v1/integrations/magento.py
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.ecommerce_config import EcommerceConfig
from datetime import datetime
import logging
import hashlib
import hmac

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/magento", tags=["Magento Integration"])

@router.post("/webhook/cart-updated/{business_id}")
async def handle_magento_cart(
    business_id: int, 
    request: Request, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Receives 'quote' updates from Magento 2.
    """
    stmt = select(EcommerceConfig).where(
        EcommerceConfig.business_id == business_id,
        EcommerceConfig.provider == "magento",
        EcommerceConfig.active == True
    )
    config = (await db.execute(stmt)).scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Magento integration not found")
    
    # Verify Signature (Custom header usually configured in Magento Webhook module)
    signature = request.headers.get("X-Magento-Signature")
    body_bytes = await request.body()
    secret = config.credentials.get("webhook_secret", "").encode("utf-8")
    
    if secret and signature:
        # Simple SHA256 hex digest check often used
        expected = hmac.new(secret, body_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            # Try plain SHA1 just in case legacy
             expected_sha1 = hmac.new(secret, body_bytes, hashlib.sha1).hexdigest()
             if not hmac.compare_digest(expected_sha1, signature):
                 raise HTTPException(status_code=401, detail="Invalid Magento signature")

    try:
        data = await request.json()
        # Magento Quote Payload Assumption:
        # { "entity_id": "...", "items": [...], "billing_address": {"telephone": "..."} }
        
        external_cart_id = data.get("entity_id") or data.get("id")
        
        # Phone extraction
        phone = None
        if "billing_address" in data and data["billing_address"]:
            phone = data["billing_address"].get("telephone")
        
        if not phone and "customer" in data:
            phone = data["customer"].get("email") # Fallback ? No, need phone for WA.
            # Assuming phone might be in custom_attributes if strictly configured
            
        if not phone:
             # Try extension attributes
             ext = data.get("extension_attributes", {})
             if "shipping_assignments" in ext:
                 # Deep dive logic... simplified for now
                 pass
             logger.warning(f"Magento Cart {external_cart_id} missing phone.")
             return {"status": "skipped", "reason": "missing_phone"}

        phone = phone.strip().replace(" ", "").replace("-", "")

        # Upsert Cart
        stmt = select(Cart).where(
            Cart.business_id == business_id,
            (Cart.external_id == str(external_cart_id)) | 
            ((Cart.user_phone == phone) & (Cart.is_active == True))
        )
        cart = (await db.execute(stmt)).scalar_one_or_none()
        
        if not cart:
            cart = Cart(
                business_id=business_id,
                user_phone=phone,
                source="magento",
                external_id=str(external_cart_id),
                is_active=True,
                status="active"
            )
            db.add(cart)
            await db.flush()
        else:
            cart.external_id = str(external_cart_id)
            cart.source = "magento"
            cart.last_interaction = datetime.utcnow()
            cart.last_notified_at = None
            
        # Sync Items
        from sqlalchemy import delete
        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        
        items = data.get("items", [])
        for item in items:
            sku = item.get("sku")
            qty = item.get("qty", 1)
            
            # Magento relies heavily on SKU
            p_stmt = select(Product).where(
                Product.business_id == business_id,
                Product.sku == sku,
                Product.provider == "magento"
            )
            product = (await db.execute(p_stmt)).scalar_one_or_none()
            
            if product:
                cart_item = CartItem(
                    cart_id=cart.id,
                    product_id=product.id,
                    quantity=qty
                )
                db.add(cart_item)

        await db.commit()
        return {"status": "success", "cart_id": cart.id}
    except Exception as e:
        logger.error(f"Error processing Magento webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Processing error")
