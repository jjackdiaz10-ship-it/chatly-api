# app/models/business_channel.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class BusinessChannel(Base):
    __tablename__ = "business_channels"

    id = Column(Integer, primary_key=True)

    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    
    # Meta integration fields
    account_id = Column(String, nullable=True)  # Phone Number ID (WSP) or IG Business ID
    token = Column(String, nullable=True)  # Access Token
    metadata_json = Column(JSON, nullable=True, default={})  # Extra data like waba_id
    active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    business = relationship("Business", back_populates="channels")
    channel = relationship("Channel", back_populates="business_channels")
