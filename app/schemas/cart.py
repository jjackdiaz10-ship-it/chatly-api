# app/schemas/cart.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.product import ProductOut

class CartItemBase(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: Optional[int] = None

class CartItemOut(CartItemBase):
    id: int
    cart_id: int
    product: Optional[ProductOut] = None

    class Config:
        from_attributes = True

class CartBase(BaseModel):
    user_phone: str
    is_active: bool = True
    metadata_json: str = "{}"

class CartCreate(CartBase):
    business_id: int

class CartUpdate(BaseModel):
    is_active: Optional[bool] = None
    metadata_json: Optional[str] = None

class CartOut(CartBase):
    id: int
    business_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[CartItemOut] = []

    class Config:
        from_attributes = True
