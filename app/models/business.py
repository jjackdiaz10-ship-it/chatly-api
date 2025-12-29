# app/models/business.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True)

    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    members = relationship("BusinessUser", back_populates="business")
    channels = relationship("BusinessChannel", back_populates="business")
    products = relationship("Product", back_populates="business")
    categories = relationship("Category", back_populates="business")
