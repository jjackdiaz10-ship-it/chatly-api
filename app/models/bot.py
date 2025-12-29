# app/models/bot.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    bot_type = Column(String, default="custom_flow") # AI_SALES, CUSTOM_FLOW, etc
    is_active = Column(Boolean, default=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True)
    
    # New fields for system integration
    config = Column(JSON, default={}, nullable=True)
    flow_id = Column(Integer, ForeignKey("flows.id"), nullable=True)
    
    # Hybrid Engine Layer
    hybrid_mode = Column(Boolean, default=True)
    rule_set = Column(JSON, default=[], nullable=True) # [{"pattern": "hola", "response": "¡Hola! ¿En qué puedo ayudarte?"}]

    # Relaciones
    flow = relationship("Flow", back_populates="bots", foreign_keys="[Bot.flow_id]")

    channels = relationship(
        "BotChannel",
        back_populates="bot",
        cascade="all, delete-orphan"
    )

