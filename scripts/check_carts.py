import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import AsyncSessionLocal
from app.models.cart import Cart, CartItem
from app.models.product import Product

async def check_carts():
    async with AsyncSessionLocal() as db:
        print("\n--- INSPECCIONANDO CARRITOS ACTIVOS ---")
        stmt = (
            select(Cart)
            .where(Cart.is_active == True)
            .options(
                selectinload(Cart.items).selectinload(CartItem.product)
            )
            .order_by(Cart.last_interaction.desc())
        )
        result = await db.execute(stmt)
        carts = result.scalars().all()
        
        if not carts:
            print("❌ No se encontraron carritos activos.")
        
        for cart in carts:
            print(f"\n[CART] ID: {cart.id} | Business ID: {cart.business_id} | Phone: {cart.user_phone}")
            print(f"   Status: {cart.status} | Last Interaction: {cart.last_interaction}")
            
            if not cart.items:
                print("   (VACIO - Sin productos asociados)")
            else:
                total = 0
                for item in cart.items:
                    prod_name = item.product.name if item.product else "[Producto Eliminado]"
                    subtotal = item.quantity * (item.product.price if item.product else 0)
                    total += subtotal
                    print(f"   - {item.quantity} x {prod_name} (ID: {item.product_id}) = ${subtotal:,.0f}")
                print(f"   TOTAL: ${total:,.0f}")

if __name__ == "__main__":
    asyncio.run(check_carts())
