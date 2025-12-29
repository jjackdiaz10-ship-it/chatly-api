# app/schemas/widget_config.py
from pydantic import BaseModel
from typing import Optional

class WidgetConfigBase(BaseModel):
    color: str = "#8b5cf6"
    position: str = "bottom-right"
    welcome_message: str = "¡Hola! ¿En qué puedo ayudarte?"

class WidgetConfigCreate(WidgetConfigBase):
    business_id: int

class WidgetConfigUpdate(BaseModel):
    color: Optional[str] = None
    position: Optional[str] = None
    welcome_message: Optional[str] = None

class WidgetConfigOut(WidgetConfigBase):
    id: int
    business_id: int

    class Config:
        from_attributes = True
