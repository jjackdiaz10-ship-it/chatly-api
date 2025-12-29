from pydantic import BaseModel

class BusinessUserBase(BaseModel):
    business_id: int
    user_id: int

class BusinessUserCreate(BaseModel):
    business_id: int
    user_id: int

class BusinessUserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None

class BusinessUserOut(BaseModel):
    id: int
    business_id: int
    user_id: int
    role: str
    is_active: bool

    class Config:
        from_attributes = True
