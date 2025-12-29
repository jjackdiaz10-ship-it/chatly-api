# app/models/ecommerce_config.py
from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Enum as SqlEnum, Boolean
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import enum

class EcommerceProvider(str, enum.Enum):
    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"
    PRESTASHOP = "prestashop"
    MAGENTO = "magento"
    CUSTOM = "custom"

class EcommerceConfig(Base):
    __tablename__ = "ecommerce_configs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    provider = Column(SqlEnum(EcommerceProvider), nullable=False)
    store_url = Column(String, nullable=False)
    
    # API credentials (called 'credentials' by frontend spec)
    credentials = Column(JSON, nullable=False, default={})
    
    active = Column(Boolean, default=True)
    
    # Settings for the floating chat widget
    widget_settings = Column(JSON, nullable=True, default={
        "color": "#007bff",
        "position": "bottom-right",
        "welcome_message": "Hello! How can I help you today?"
    })

    business = relationship("Business")
