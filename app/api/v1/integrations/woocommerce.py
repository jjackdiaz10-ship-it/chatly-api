# app/api/v1/integrations/woocommerce.py
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.business import Business
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.ecommerce_config import EcommerceConfig
from datetime import datetime
import logging
import json
import hashlib
import hmac
import base64

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/woocommerce", tags=["WooCommerce Integration"])

@router.post("/webhook/cart-updated/{business_id}")
async def handle_cart_update(
    business_id: int, 
    request: Request, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Receives 'woocommerce_cart_updated' webhooks.
    Expected payload: JSON with cart data (customer info + line items).
    NOTE: Requires a WooCommerce plugin ('WooCommerce Cart Rest API' or similar) 
    that sends cart data on abandonment/update events.
    """
    
    # 1. Verify Business Integrations
    stmt = select(EcommerceConfig).where(
        EcommerceConfig.business_id == business_id,
        EcommerceConfig.provider == "woocommerce",
        EcommerceConfig.active == True
    )
    config = (await db.execute(stmt)).scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="WooCommerce integration not found for this business")
    
    # 2. Verify Signature (Security)
    # WooCommerce sends X-WC-Webhook-Signature (HMAC-SHA256 of body)
    signature = request.headers.get("X-WC-Webhook-Signature")
    if not signature:
       # For dev/testing we might skip if not provided, but in strict mode we raise 401
       pass 
       
    body_bytes = await request.body()
    secret = config.credentials.get("webhook_secret", "").encode("utf-8")
    
    if secret and signature:
        expected = base64.b64encode(hmac.new(secret, body_bytes, hashlib.sha256).digest()).decode()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 3. Process Cart Data
    try:
        data = await request.json()
        
        # Mapping logic depends on the specific WooCommerce Webhook payload structure.
        # This assumes a standard structure often used by 'WooCommerce Cart abandonment' plugins.
        
        # Example Payload:
        # {
        #   "cart_hash": "abc12345",
        #   "customer": {"email": "...", "phone": "+50212345678"},
        #   "items": [{"product_id": 101, "quantity": 2, "line_total": 50.00}],
        #   "totals": {"total": 100.00}
        # }
        
        external_cart_id = data.get("cart_hash") or data.get("id")
        customer = data.get("customer", {})
        phone = customer.get("billing_phone") or customer.get("phone")
        
        if not phone:
             # Try to normalize if only email? 
             # For WhatsApp recovery we NEED phone.
             # Log warning and exit
             logger.warning(f"WooCommerce Cart {external_cart_id} missing phone number. Skipping.")
             return {"status": "skipped", "reason": "missing_phone"}

        # Normalize Phone (Simple fallback)
        # TODO: Use a proper phone validation library
        phone = phone.strip().replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            # Assume default country code if missing? Dangerous.
            # Best practice: configure default country code in Business settings.
            pass

        # 4. Upsert Cart in Chatly DB
        # Check if cart exists by external_id OR match by active user phone
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
                source="woocommerce",
                external_id=str(external_cart_id),
                is_active=True,
                status="active"
            )
            db.add(cart)
            await db.flush()
        else:
            # Update metadata
            cart.external_id = str(external_cart_id) # Ensure link
            cart.source = "woocommerce"
            # Refresh timestamp to reset abandonment timer
            cart.last_interaction = datetime.utcnow()
            cart.last_notified_at = None # Reset notification if user eventually came back
            
        # 5. Sync Items
        # Clear old items to full sync
        from sqlalchemy import delete
        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        
        items = data.get("items", [])
        for item in items:
            ext_product_id = str(item.get("product_id"))
            quantity = item.get("quantity", 1)
            
            # Find internal product ID by external ID
            p_stmt = select(Product).where(
                Product.business_id == business_id,
                Product.external_id == ext_product_id,
                Product.provider == "woocommerce"
            )
            product = (await db.execute(p_stmt)).scalar_one_or_none()
            
            if product:
                cart_item = CartItem(
                    cart_id=cart.id,
                    product_id=product.id,
                    quantity=quantity
                )
                db.add(cart_item)
            else:
                logger.warning(f"Product {ext_product_id} not found in Chatly sync. Skipping item.")
                
        await db.commit()
        
        logger.info(f"WooCommerce cart {external_cart_id} synced for {phone}")
        return {"status": "success", "cart_id": cart.id}
        
    except Exception as e:
        logger.error(f"Error processing WooCommerce webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal processing error")
