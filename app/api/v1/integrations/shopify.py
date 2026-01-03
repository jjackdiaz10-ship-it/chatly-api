# app/api/v1/integrations/shopify.py
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
import base64

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/shopify", tags=["Shopify Integration"])

@router.post("/webhook/cart-updated/{business_id}")
async def handle_shopify_cart(
    business_id: int, 
    request: Request, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Receives 'carts/update' or 'checkouts/update' webhooks from Shopify.
    """
    
    # 1. Verify Configuration
    stmt = select(EcommerceConfig).where(
        EcommerceConfig.business_id == business_id,
        EcommerceConfig.provider == "shopify",
        EcommerceConfig.active == True
    )
    config = (await db.execute(stmt)).scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Shopify integration not found")
    
    # 2. Verify HMAC Signature
    signature = request.headers.get("X-Shopify-Hmac-Sha256")
    body_bytes = await request.body()
    secret = config.credentials.get("webhook_secret", "").encode("utf-8")
    
    if secret and signature:
        digest = hmac.new(secret, body_bytes, hashlib.sha256).digest()
        computed_hmac = base64.b64encode(digest).decode()
        if not hmac.compare_digest(computed_hmac, signature):
            raise HTTPException(status_code=401, detail="Invalid Shopify signature")

    # 3. Process Payload
    try:
        data = await request.json()
        # Shopify Payload Structure:
        # { "id": "token...", "token": "...", "line_items": [...], "phone": "+123...", "customer": {...} }
        
        external_cart_id = data.get("token") or data.get("id")
        
        # Phone logic: Shopify puts phone in root (checkout) or inside customer object
        phone = data.get("phone")
        if not phone and "customer" in data and data["customer"]:
            phone = data["customer"].get("phone") or data["customer"].get("default_address", {}).get("phone")
            
        if not phone:
            logger.warning(f"Shopify Cart {external_cart_id} missing phone. Skipping.")
            return {"status": "skipped", "reason": "missing_phone"}

        # Normalize Phone
        phone = phone.strip().replace(" ", "").replace("-", "")
        
        # 4. Upsert Cart
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
                source="shopify",
                external_id=str(external_cart_id),
                is_active=True,
                status="active"
            )
            db.add(cart)
            await db.flush()
        else:
            cart.external_id = str(external_cart_id)
            cart.source = "shopify"
            cart.last_interaction = datetime.utcnow()
            cart.last_notified_at = None
            
        # 5. Sync Items
        from sqlalchemy import delete
        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        
        # Shopify line_items structure
        items = data.get("line_items", [])
        for item in items:
            # Shopify Variant ID is usually the SKU key
            valid_id = item.get("variant_id") or item.get("product_id")
            quantity = item.get("quantity", 1)
            
            # Find product
            p_stmt = select(Product).where(
                Product.business_id == business_id,
                Product.external_id == str(valid_id),
                Product.provider == "shopify"
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
                # Fallback: Try matching by name/SKU if exact ID fails (common in variant mismatches)
                sku = item.get("sku")
                if sku:
                    p_sku = select(Product).where(
                        Product.business_id == business_id,
                        Product.sku == sku
                    )
                    product = (await db.execute(p_sku)).scalar_one_or_none()
                    if product:
                         cart_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
                         db.add(cart_item)

        await db.commit()
        logger.info(f"Shopify cart {external_cart_id} synced for {phone}")
        return {"status": "success", "cart_id": cart.id}

    except Exception as e:
        logger.error(f"Error processing Shopify webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Processing error")
