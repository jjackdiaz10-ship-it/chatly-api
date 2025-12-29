# app/api/v1/payments.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.payment_config import PaymentConfig
from app.schemas.payment_config import PaymentConfigCreate, PaymentConfigUpdate, PaymentConfigOut
from typing import List

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("/config", response_model=List[PaymentConfigOut])
async def get_payment_configs(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(PaymentConfig))
    return res.scalars().all()

@router.post("/config", response_model=PaymentConfigOut)
async def create_payment_config(data: PaymentConfigCreate, db: AsyncSession = Depends(get_db)):
    config = PaymentConfig(**data.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config

@router.put("/config/{id}", response_model=PaymentConfigOut)
async def update_payment_config(id: int, data: PaymentConfigUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(PaymentConfig).where(PaymentConfig.id == id))
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Payment config not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)
    
    await db.commit()
    await db.refresh(config)
    return config

@router.delete("/config/{id}")
async def delete_payment_config(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(PaymentConfig).where(PaymentConfig.id == id))
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Payment config not found")
    await db.delete(config)
    await db.commit()
    return {"status": "deleted"}
