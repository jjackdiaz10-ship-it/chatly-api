# app/models/widget_config.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class WidgetConfig(Base):
    __tablename__ = "widget_configs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, unique=True)
    
    color = Column(String, default="#8b5cf6")
    position = Column(String, default="bottom-right")  # bottom-right | bottom-left
    welcome_message = Column(String, default="¡Hola! ¿En qué puedo ayudarte?")

    business = relationship("Business")
