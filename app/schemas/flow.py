# app/schemas/flow.py
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class ViewportSchema(BaseModel):
    x: float = 0
    y: float = 0
    zoom: float = 1

class FlowBase(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: List[Any] = []
    edges: List[Any] = []
    viewport: Optional[Dict[str, Any]] = {"x": 0, "y": 0, "zoom": 1}
    business_id: Optional[int] = None
    bot_id: Optional[int] = None

class FlowCreate(FlowBase):
    pass

class FlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[Any]] = None
    edges: Optional[List[Any]] = None
    viewport: Optional[Dict[str, Any]] = None
    bot_id: Optional[int] = None

class FlowOut(FlowBase):
    id: int

    class Config:
        from_attributes = True
