# app/models/flow.py
from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Flow(Base):
    __tablename__ = "flows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    # Store the flow logic as a JSON structure
    nodes = Column(JSON, nullable=False, default=[])
    edges = Column(JSON, nullable=False, default=[])
    viewport = Column(JSON, nullable=True, default={"x": 0, "y": 0, "zoom": 1})

    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=True)

    bots = relationship("Bot", back_populates="flow", foreign_keys="[Bot.flow_id]")
    business = relationship("Business")
