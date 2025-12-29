from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class BotCreate(BaseModel):
    name: str
    bot_type: str = "custom_flow"
    is_active: bool = True
    business_id: Optional[int] = None
    config: Dict[str, Any] = {}
    flow_id: Optional[int] = None
    hybrid_mode: bool = True
    rule_set: List[Dict[str, Any]] = []

class BotUpdate(BaseModel):
    name: Optional[str] = None
    bot_type: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    flow_id: Optional[int] = None
    hybrid_mode: Optional[bool] = None
    rule_set: Optional[List[Dict[str, Any]]] = None

class BotOut(BaseModel):
    id: int
    name: str
    bot_type: str
    is_active: bool
    business_id: Optional[int]
    config: Dict[str, Any]
    flow_id: Optional[int]
    hybrid_mode: bool
    rule_set: List[Dict[str, Any]]

    class Config:
        from_attributes = True