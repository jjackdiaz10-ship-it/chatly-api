# app/services/ecommerce_sync_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ecommerce_config import EcommerceConfig
from app.models.product import Product
from app.models.category import Category
from app.services.ecommerce_factory import EcommerceFactory
from typing import Optional

class EcommerceSyncService:
    @staticmethod
    async def sync_products(db: AsyncSession, business_id: int):
        # Fetch the active eCommerce config for this business
        res = await db.execute(
            select(EcommerceConfig).where(EcommerceConfig.business_id == business_id)
        )
        config = res.scalars().first()
        
        if not config:
            raise ValueError("No eCommerce configuration found for this business")
            
        adapter = EcommerceFactory.get_adapter(config.provider, config.store_url, config.credentials)
        external_products = await adapter.fetch_products()
        
        # Determine a default category for the business (or create one)
        cat_res = await db.execute(select(Category).where(Category.business_id == business_id))
        category = cat_res.scalars().first()
        if not category:
            category = Category(name="General", business_id=business_id)
            db.add(category)
            await db.flush()

        for ep in external_products:
            # Check if product already exists
            p_res = await db.execute(
                select(Product).where(
                    Product.business_id == business_id,
                    Product.external_id == ep["external_id"],
                    Product.provider == config.provider
                )
            )
            product = p_res.scalars().first()
            
            if product:
                # Update
                product.name = ep["name"]
                product.description = ep["description"]
                product.price = ep["price"]
                product.metadata_json = ep["metadata"]
            else:
                # Create
                product = Product(
                    business_id=business_id,
                    category_id=category.id,
                    name=ep["name"],
                    description=ep["description"],
                    price=ep["price"],
                    external_id=ep["external_id"],
                    provider=config.provider,
                    metadata_json=ep["metadata"]
                )
                db.add(product)
        
        await db.commit()
        return len(external_products)
