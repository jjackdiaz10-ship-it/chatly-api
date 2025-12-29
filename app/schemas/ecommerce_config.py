# app/schemas/ecommerce_config.py
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.models.ecommerce_config import EcommerceProvider

class EcommerceConfigBase(BaseModel):
    business_id: int
    provider: EcommerceProvider
    store_url: str
    credentials: Dict[str, Any] = {}
    active: bool = True

class EcommerceConfigCreate(EcommerceConfigBase):
    pass

class EcommerceConfigUpdate(BaseModel):
    provider: Optional[EcommerceProvider] = None
    store_url: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None

class EcommerceConfigOut(EcommerceConfigBase):
    id: int

    class Config:
        from_attributes = True
