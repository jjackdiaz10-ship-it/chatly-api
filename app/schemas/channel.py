from pydantic import BaseModel

class ChannelCreate(BaseModel):
    name: str
    description: str | None = None

class ChannelUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
