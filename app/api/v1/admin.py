# app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.session import get_db
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.schemas.plan import SubscriptionCreate, SubscriptionOut
from app.api.deps import get_current_user
from datetime import datetime, timedelta

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

@router.post("/assign-subscription", response_model=SubscriptionOut)
async def assign_subscription_admin(
    sub_in: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Super-Admin override: Assign or upgrade a business to a plan.
    """
    from app.api.v1.plans import create_subscription
    return await create_subscription(sub_in, db, current_user)
