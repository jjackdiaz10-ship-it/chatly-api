# app/models/business_user.py
from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class BusinessUser(Base):
    __tablename__ = "business_users"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    role = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    user = relationship("User", back_populates="memberships")
    business = relationship("Business", back_populates="members")
