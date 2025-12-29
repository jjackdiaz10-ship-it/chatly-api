# app/schemas/product.py
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, Dict, Any
from app.models.ecommerce_config import EcommerceProvider

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    is_active: bool = True
    category_id: int
    business_id: Optional[int] = None
    external_id: Optional[str] = None
    provider: Optional[EcommerceProvider] = None
    metadata_json: Dict[str, Any] = {}

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    is_active: Optional[bool] = None
    external_id: Optional[str] = None
    provider: Optional[EcommerceProvider] = None
    metadata_json: Optional[Dict[str, Any]] = None

class ProductOut(ProductBase):
    id: int

    class Config:
        from_attributes = True
