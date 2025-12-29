# app/schemas/payment_config.py
from pydantic import BaseModel
from typing import Optional, Dict, Any

class PaymentConfigBase(BaseModel):
    business_id: int
    provider: str
    credentials: Dict[str, Any] = {}
    is_active: bool = True

class PaymentConfigCreate(PaymentConfigBase):
    pass

class PaymentConfigUpdate(BaseModel):
    provider: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class PaymentConfigOut(PaymentConfigBase):
    id: int

    class Config:
        from_attributes = True
