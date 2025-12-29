# app/schemas/category.py
from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    business_id: int
    description: str | None = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool

    class Config:
        from_attributes = True
