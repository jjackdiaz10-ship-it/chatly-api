# app/api/v1/plans.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.schemas.plan import PlanOut, SubscriptionOut
from app.api.deps import get_current_user

router = APIRouter(prefix="/plans", tags=["Plans & Subscriptions"])

@router.get("/", response_model=List[PlanOut])
async def list_available_plans(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Plan))
    return res.scalars().all()

@router.get("/my-subscription/{business_id}", response_model=SubscriptionOut)
async def get_my_subscription(
    business_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    stmt = select(Subscription).where(Subscription.business_id == business_id, Subscription.is_active == True)
    res = await db.execute(stmt)
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found")
    return sub
