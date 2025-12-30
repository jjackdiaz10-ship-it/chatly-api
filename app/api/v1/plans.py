# app/api/v1/plans.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.plan import Plan
from app.models.subscription import Subscription
from sqlalchemy.orm import selectinload
from app.schemas.plan import PlanOut, SubscriptionOut, SubscriptionCreate, SubscriptionUpdate
from app.api.deps import get_current_user
from datetime import datetime, timedelta

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
    stmt = (
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.business_id == business_id, Subscription.is_active == True)
    )
    res = await db.execute(stmt)
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found")
    return sub

@router.post("/subscribe", response_model=SubscriptionOut)
async def create_subscription(
    sub_in: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Assigns or changes a business's subscription.
    Deactivates any previous active subscriptions for that business.
    """
    # 1. Deactivate old ones
    from sqlalchemy import update
    await db.execute(
        update(Subscription)
        .where(Subscription.business_id == sub_in.business_id)
        .values(is_active=False)
    )
    
    # 2. Create new
    expiry = datetime.utcnow() + timedelta(days=30) if sub_in.billing_cycle == "monthly" else datetime.utcnow() + timedelta(days=365)
    new_sub = Subscription(
        business_id=sub_in.business_id,
        plan_id=sub_in.plan_id,
        billing_cycle=sub_in.billing_cycle,
        is_active=True,
        current_period_end=expiry
    )
    
    db.add(new_sub)
    await db.commit()
    await db.refresh(new_sub)
    
    # Re-fetch with plan info
    stmt = select(Subscription).options(selectinload(Subscription.plan)).where(Subscription.id == new_sub.id)
    return (await db.execute(stmt)).scalar_one()

@router.put("/subscription/{sub_id}", response_model=SubscriptionOut)
async def update_subscription(
    sub_id: int,
    sub_update: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    stmt = select(Subscription).where(Subscription.id == sub_id)
    res = await db.execute(stmt)
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    update_data = sub_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sub, field, value)
        
    await db.commit()
    await db.refresh(sub)
    
    stmt = select(Subscription).options(selectinload(Subscription.plan)).where(Subscription.id == sub.id)
    return (await db.execute(stmt)).scalar_one()
