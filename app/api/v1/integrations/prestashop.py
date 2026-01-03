# app/api/v1/integrations/prestashop.py
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

router = APIRouter(prefix="/integrations/prestashop", tags=["PrestaShop Integration"])

@router.post("/webhook/cart-updated/{business_id}")
async def handle_prestashop_cart(
    business_id: int, 
    request: Request, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Receives cart updates from PrestaShop (via generic webhook module).
    """
    stmt = select(EcommerceConfig).where(
        EcommerceConfig.business_id == business_id,
        EcommerceConfig.provider == "prestashop",
        EcommerceConfig.active == True
    )
    config = (await db.execute(stmt)).scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="PrestaShop integration not found")
    
    # Verify Token (PrestaShop usually uses a simple secure_key URL param or header)
    # We will check a custom header X-Presta-Token
    token = request.headers.get("X-Presta-Token")
    secret = config.credentials.get("webhook_secret", "")
    
    if secret and token != secret:
        raise HTTPException(status_code=401, detail="Invalid PrestaShop token")

    try:
        data = await request.json()
        # PrestaShop Payload Assumption:
        # { "cart": { "id": 123, "associations": { "cart_rows": [...] } }, "customer": { "phone": "..." } }
        
        # Flattened structure is also common depending on module
        cart_data = data.get("cart", data)
        external_cart_id = cart_data.get("id")
        
        customer = data.get("customer", {})
        phone = customer.get("phone_mobile") or customer.get("phone")
        
        # Or sometimes in address
        if not phone and "address" in data:
            phone = data["address"].get("phone_mobile") or data["address"].get("phone")

        if not phone:
            logger.warning(f"PrestaShop Cart {external_cart_id} missing phone.")
            return {"status": "skipped", "reason": "missing_phone"}

        phone = phone.strip().replace(" ", "")

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
                source="prestashop",
                external_id=str(external_cart_id),
                is_active=True,
                status="active"
            )
            db.add(cart)
            await db.flush()
        else:
            cart.external_id = str(external_cart_id)
            cart.source = "prestashop"
            cart.last_interaction = datetime.utcnow()
            cart.last_notified_at = None
            
        # Sync Items
        from sqlalchemy import delete
        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        
        # Rows logic
        rows = cart_data.get("associations", {}).get("cart_rows", [])
        if not rows and "products" in cart_data:
             rows = cart_data["products"] # Alternate structure

        for row in rows:
            prod_id = str(row.get("product_id") or row.get("id_product"))
            qty = row.get("quantity", 1)
            
            p_stmt = select(Product).where(
                Product.business_id == business_id,
                Product.external_id == prod_id,
                Product.provider == "prestashop"
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
        logger.error(f"Error processing PrestaShop webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Processing error")
