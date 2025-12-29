# app/models/product.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric, JSON, Enum as SqlEnum
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.models.ecommerce_config import EcommerceProvider


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, default=0)
    sku = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Provider-specific fields
    external_id = Column(String, nullable=True, index=True)
    provider = Column(SqlEnum(EcommerceProvider), nullable=True)
    metadata_json = Column(JSON, nullable=True, default={})

    category = relationship("Category", back_populates="products")
    business = relationship("Business", back_populates="products")
    
