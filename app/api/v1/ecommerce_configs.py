# app/api/v1/ecommerce_configs.py
from app.core.crud_factory import generate_crud
from app.models.ecommerce_config import EcommerceConfig
from app.schemas.ecommerce_config import EcommerceConfigCreate, EcommerceConfigUpdate
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.ecommerce_sync_service import EcommerceSyncService

router = generate_crud(
    model=EcommerceConfig,
    schema_create=EcommerceConfigCreate,
    schema_update=EcommerceConfigUpdate,
    prefix="/ecommerce-configs",
    tag="Ecommerce Configs",
    permissions={
        "create": "ecommerce:create",
        "view": "ecommerce:view",
        "update": "ecommerce:update",
        "delete": "ecommerce:delete"
    }
)

@router.post("/{business_id}/sync")
async def sync_ecommerce_products(business_id: int, db: AsyncSession = Depends(get_db)):
    count = await EcommerceSyncService.sync_products(db, business_id)
    return {"status": "ok", "synced_products": count}
