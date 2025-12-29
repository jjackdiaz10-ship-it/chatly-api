# app/api/v1/ecommerce.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.ecommerce_config import EcommerceConfig, EcommerceProvider
from app.schemas.ecommerce_config import EcommerceConfigCreate, EcommerceConfigUpdate, EcommerceConfigOut
from app.services.ecommerce_sync_service import EcommerceSyncService
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/ecommerce", tags=["Ecommerce"])

# --- Integrations CRUD ---
@router.get("/integrations", response_model=List[EcommerceConfigOut])
async def get_integrations(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(EcommerceConfig))
    return res.scalars().all()

@router.post("/integrations", response_model=EcommerceConfigOut)
async def create_integration(data: EcommerceConfigCreate, db: AsyncSession = Depends(get_db)):
    config = EcommerceConfig(**data.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config

@router.put("/integrations/{id}", response_model=EcommerceConfigOut)
async def update_integration(id: int, data: EcommerceConfigUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(EcommerceConfig).where(EcommerceConfig.id == id))
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)
    
    await db.commit()
    await db.refresh(config)
    return config

@router.delete("/integrations/{id}")
async def delete_integration(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(EcommerceConfig).where(EcommerceConfig.id == id))
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    await db.delete(config)
    await db.commit()
    return {"status": "deleted"}

# --- Sync Endpoint ---
class SyncRequest(BaseModel):
    integration_id: int

@router.post("/sync")
async def sync_products(data: SyncRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(EcommerceConfig).where(EcommerceConfig.id == data.integration_id))
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    count = await EcommerceSyncService.sync_products(db, config.business_id)
    return {"status": "success", "products_synced": count, "message": f"Synced {count} products"}
