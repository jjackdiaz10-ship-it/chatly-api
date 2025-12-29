# app/models/payment_config.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class PaymentConfig(Base):
    __tablename__ = "payment_configs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    provider = Column(String, nullable=False)  # stripe, paypal, mercadopago, etc.
    
    # Credentials stored as JSON (ideally encrypted in production)
    # e.g., {"api_key": "sk_test_...", "public_key": "pk_test_..."}
    credentials = Column(JSON, nullable=False, default={})
    
    is_active = Column(Boolean, default=True)

    business = relationship("Business")
