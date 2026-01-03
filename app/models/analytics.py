# app/models/analytics.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean, Enum as SqlEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base
import enum

class EventType(str, enum.Enum):
    """Types of trackable events"""
    CART_CREATED = "cart_created"
    CART_ABANDONED = "cart_abandoned"
    RECOVERY_SENT = "recovery_sent"
    CART_RECOVERED = "cart_recovered"
    CHECKOUT_COMPLETED = "checkout_completed"
    PAYMENT_COMPLETED = "payment_completed"
    AI_FALLBACK = "ai_fallback"
    FAQ_HIT = "faq_hit"
    LEARNING_SUGGESTION_CREATED = "learning_suggestion_created"

class CartRecoveryEvent(Base):
    """Tracks all cart-related events for analytics"""
    __tablename__ = "cart_recovery_events"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=True)
    user_phone = Column(String, nullable=False, index=True)
    
    event_type = Column(SqlEnum(EventType), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Event-specific data
    cart_value = Column(Float, nullable=True)
    discount_code = Column(String, nullable=True)
    discount_percent = Column(Float, nullable=True)
    discount_amount = Column(Float, nullable=True)
    
    # Recovery tracking
    time_to_recovery_hours = Column(Float, nullable=True)  # Time from abandonment to recovery
    recovery_channel = Column(String, nullable=True)  # whatsapp, email, sms
    
    # Additional metadata
    metadata_json = Column(JSON, default={})
    
    # Relationships
    business = relationship("Business")
    cart = relationship("Cart")

class AIPerformanceMetric(Base):
    """Tracks AI assistant performance metrics"""
    __tablename__ = "ai_performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Intent detection
    intent_detected = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Response source
    response_source = Column(String, nullable=False)  # faq, ai_fallback, rule_engine
    ai_model_used = Column(String, nullable=True)  # gemini-1.5-flash, etc.
    
    # Performance
    response_time_ms = Column(Integer, nullable=True)
    
    # Conversation tracking
    user_phone = Column(String, nullable=False, index=True)
    user_message = Column(String, nullable=True)
    bot_response = Column(String, nullable=True)
    
    # Conversion tracking
    led_to_cart_action = Column(Boolean, default=False)  # Did this interaction lead to add_to_cart or checkout?
    
    metadata_json = Column(JSON, default={})
    
    business = relationship("Business")

class CustomerLifetimeValue(Base):
    """Tracks CLV for each customer"""
    __tablename__ = "customer_lifetime_values"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    user_phone = Column(String, nullable=False, index=True)
    
    # CLV metrics
    total_purchases = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    avg_order_value = Column(Float, default=0.0)
    
    # Engagement
    first_purchase_date = Column(DateTime(timezone=True), nullable=True)
    last_purchase_date = Column(DateTime(timezone=True), nullable=True)
    days_since_last_purchase = Column(Integer, nullable=True)
    
    # Recovery stats
    carts_abandoned = Column(Integer, default=0)
    carts_recovered = Column(Integer, default=0)
    recovery_rate = Column(Float, default=0.0)  # Percentage
    
    # Risk score (churn prediction)
    churn_risk_score = Column(Float, default=0.0)  # 0-1, higher = more likely to churn
    
    # Calculated fields (updated periodically)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    business = relationship("Business")
    
    # Unique constraint on business + user_phone
    __table_args__ = (
        {"schema": None},
    )
