# app/models/plan.py
from sqlalchemy import Column, Integer, String, Float, JSON
from app.db.base_class import Base

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False) # e.g., "Vantix Core", "Vantix Ultra", "Vantix Prime", "Iris Lite"
    price_monthly = Column(Float, nullable=False)
    price_yearly = Column(Float, nullable=False)
    
    # Limits and Features
    max_conversations = Column(Integer, default=1000)
    max_users = Column(Integer, default=1)
    max_funnels = Column(Integer, default=1)
    
    features = Column(JSON, default={}) # e.g., {"ads": true, "phone": false, "api_access": true}
