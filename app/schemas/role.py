from pydantic import BaseModel

class RoleCreate(BaseModel):
    name: str
    permissions: list[str] = []

class RoleUpdate(BaseModel):
    name: str | None = None
    permissions: list[str] = []
