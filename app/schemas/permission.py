from pydantic import BaseModel

class PermissionCreate(BaseModel):
    code: str

class PermissionUpdate(BaseModel):
    code: str

class PermissionOut(BaseModel):
    id: int
    code: str

    class Config:
        from_attributes = True
