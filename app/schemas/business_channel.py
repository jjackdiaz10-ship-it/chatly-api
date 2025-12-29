from pydantic import BaseModel
from typing import Optional, Dict, Any

class BusinessChannelBase(BaseModel):
    business_id: Optional[int] = None
    channel_id: int
    account_id: Optional[str] = None
    token: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = {}
    active: bool = True

class BusinessChannelCreate(BusinessChannelBase):
    pass

class BusinessChannelUpdate(BaseModel):
    account_id: Optional[str] = None
    token: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None

class BusinessChannelOut(BaseModel):
    id: int
    business_id: int
    channel_id: int
    account_id: Optional[str]
    token: Optional[str] = None

    @property
    def masked_token(self):
        if self.token:
            return f"{self.token[:4]}****{self.token[-4:]}"
        return None
    metadata_json: Optional[Dict[str, Any]]
    active: bool

    class Config:
        from_attributes = True
