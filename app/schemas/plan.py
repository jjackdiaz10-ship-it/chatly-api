# app/schemas/plan.py
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class PlanBase(BaseModel):
    name: str
    price_monthly: float
    price_yearly: float
    max_conversations: int
    max_users: int
    max_funnels: int
    features: Dict[str, Any] = {}

class PlanCreate(PlanBase):
    pass

class PlanOut(PlanBase):
    id: int
    class Config:
        from_attributes = True

class SubscriptionCreate(BaseModel):
    business_id: int
    plan_id: int
    billing_cycle: str = "monthly"
    is_active: bool = True

class SubscriptionUpdate(BaseModel):
    plan_id: Optional[int] = None
    billing_cycle: Optional[str] = None
    is_active: Optional[bool] = None

class SubscriptionOut(BaseModel):
    id: int
    business_id: int
    plan_id: int
    plan: Optional[PlanOut] = None
    is_active: bool
    billing_cycle: str
    current_period_end: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
