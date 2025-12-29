from pydantic import BaseModel

class BusinessCreate(BaseModel):
    code: str
    name: str
    is_active: bool = True

class BusinessUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None

class BusinessOut(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool

    class Config:
        from_attributes = True

