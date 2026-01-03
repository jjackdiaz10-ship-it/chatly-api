# app/models/cart.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    user_phone = Column(String, nullable=False) # Key to correlate with WhatsApp user
    is_active = Column(Boolean, default=True)
    status = Column(String, default="active") # active, abandoned, recovered, paid
    source = Column(String, default="chat_native") # chat_native, woocommerce, shopify
    external_id = Column(String, nullable=True, index=True) # ID in external system
    coupon_applied = Column(String, nullable=True)
    metadata_json = Column(String, default="{}")
    last_interaction = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_notified_at = Column(DateTime(timezone=True), nullable=True)

    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")
