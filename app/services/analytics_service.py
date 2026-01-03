# app/services/analytics_service.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from app.models.analytics import CartRecoveryEvent, AIPerformanceMetric, CustomerLifetimeValue, EventType
from app.models.cart import Cart, CartItem
from app.models.product import Product
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    """
    Comprehensive analytics service for E-commerce AI metrics.
    Tracks cart recovery, AI performance, and customer lifetime value.
    """
    
    # ============================================================================
    # EVENT TRACKING
    # ============================================================================
    
    @staticmethod
    async def track_event(
        db: AsyncSession,
        business_id: int,
        event_type: EventType,
        user_phone: str,
        cart_id: Optional[int] = None,
        **kwargs
    ):
        """
        Track a cart or AI event for analytics.
        
        Args:
            db: Database session
            business_id: Business ID
            event_type: Type of event (from EventType enum)
            user_phone: Customer phone number
            cart_id: Optional cart ID
            **kwargs: Additional event-specific data (cart_value, discount_code, etc.)
        """
        try:
            event = CartRecoveryEvent(
                business_id=business_id,
                cart_id=cart_id,
                user_phone=user_phone,
                event_type=event_type,
                cart_value=kwargs.get('cart_value'),
                discount_code=kwargs.get('discount_code'),
                discount_percent=kwargs.get('discount_percent'),
                discount_amount=kwargs.get('discount_amount'),
                time_to_recovery_hours=kwargs.get('time_to_recovery_hours'),
                recovery_channel=kwargs.get('recovery_channel', 'whatsapp'),
                metadata_json=kwargs.get('metadata', {})
            )
            db.add(event)
            await db.commit()
            logger.debug(f"Tracked event: {event_type} for business {business_id}")
        except Exception as e:
            logger.error(f"Error tracking event: {e}")
    
    @staticmethod
    async def track_ai_interaction(
        db: AsyncSession,
        business_id: int,
        user_phone: str,
        user_message: str,
        bot_response: str,
        response_source: str,  # 'faq', 'ai_fallback', 'rule_engine'
        **kwargs
    ):
        """
        Track AI assistant interactions for performance analysis.
        
        Args:
            db: Database session
            business_id: Business ID
            user_phone: Customer phone
            user_message: User's message
            bot_response: Bot's response
            response_source: Where the response came from
            **kwargs: Additional data (ai_model, intent, confidence, etc.)
        """
        try:
            metric = AIPerformanceMetric(
                business_id=business_id,
                user_phone=user_phone,
                user_message=user_message[:500],  # Truncate for storage
                bot_response=bot_response[:500],
                response_source=response_source,
                ai_model_used=kwargs.get('ai_model'),
                intent_detected=kwargs.get('intent'),
                confidence_score=kwargs.get('confidence'),
                response_time_ms=kwargs.get('response_time_ms'),
                led_to_cart_action=kwargs.get('led_to_cart_action', False),
                metadata_json=kwargs.get('metadata', {})
            )
            db.add(metric)
            await db.commit()
        except Exception as e:
            logger.error(f"Error tracking AI interaction: {e}")
    
    # ============================================================================
    # CART RECOVERY METRICS
    # ============================================================================
    
    @classmethod
    async def get_cart_recovery_metrics(
        cls,
        db: AsyncSession,
        business_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Calculate cart recovery performance metrics.
        
        Returns:
            Dict with recovery rate, revenue, average time to recovery, etc.
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Count abandoned carts
        abandoned_stmt = select(func.count(CartRecoveryEvent.id)).where(
            CartRecoveryEvent.business_id == business_id,
            CartRecoveryEvent.event_type == EventType.CART_ABANDONED,
            CartRecoveryEvent.timestamp.between(start_date, end_date)
        )
        abandoned_count = (await db.execute(abandoned_stmt)).scalar() or 0
        
        # Count recovered carts
        recovered_stmt = select(func.count(CartRecoveryEvent.id)).where(
            CartRecoveryEvent.business_id == business_id,
            CartRecoveryEvent.event_type == EventType.CART_RECOVERED,
            CartRecoveryEvent.timestamp.between(start_date, end_date)
        )
        recovered_count = (await db.execute(recovered_stmt)).scalar() or 0
        
        # Count recovery messages sent
        sent_stmt = select(func.count(CartRecoveryEvent.id)).where(
            CartRecoveryEvent.business_id == business_id,
            CartRecoveryEvent.event_type == EventType.RECOVERY_SENT,
            CartRecoveryEvent.timestamp.between(start_date, end_date)
        )
        sent_count = (await db.execute(sent_stmt)).scalar() or 0
        
        # Calculate revenue from recovered carts
        revenue_stmt = select(func.sum(CartRecoveryEvent.cart_value)).where(
            CartRecoveryEvent.business_id == business_id,
            CartRecoveryEvent.event_type == EventType.CART_RECOVERED,
            CartRecoveryEvent.timestamp.between(start_date, end_date)
        )
        recovered_revenue = (await db.execute(revenue_stmt)).scalar() or 0.0
        
        # Average time to recovery
        avg_time_stmt = select(func.avg(CartRecoveryEvent.time_to_recovery_hours)).where(
            CartRecoveryEvent.business_id == business_id,
            CartRecoveryEvent.event_type == EventType.CART_RECOVERED,
            CartRecoveryEvent.timestamp.between(start_date, end_date),
            CartRecoveryEvent.time_to_recovery_hours.isnot(None)
        )
        avg_recovery_time = (await db.execute(avg_time_stmt)).scalar() or 0.0
        
        # Calculate rates
        recovery_rate = (recovered_count / abandoned_count * 100) if abandoned_count > 0 else 0
        message_conversion_rate = (recovered_count / sent_count * 100) if sent_count > 0 else 0
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "carts_abandoned": abandoned_count,
            "recovery_messages_sent": sent_count,
            "carts_recovered": recovered_count,
            "recovery_rate_percent": round(recovery_rate, 2),
            "message_conversion_rate_percent": round(message_conversion_rate, 2),
            "recovered_revenue": round(recovered_revenue, 2),
            "avg_time_to_recovery_hours": round(avg_recovery_time, 2),
            "estimated_saved_revenue": round(recovered_revenue, 2)  # Same as recovered for now
        }
    
    # ============================================================================
    # CLV TRACKING
    # ============================================================================
    
    @classmethod
    async def update_customer_clv(
        cls,
        db: AsyncSession,
        business_id: int,
        user_phone: str
    ):
        """
        Update or create CLV record for a customer.
        Recalculates all metrics from cart history.
        """
        # Get or create CLV record
        clv_stmt = select(CustomerLifetimeValue).where(
            CustomerLifetimeValue.business_id == business_id,
            CustomerLifetimeValue.user_phone == user_phone
        )
        clv = (await db.execute(clv_stmt)).scalar_one_or_none()
        
        if not clv:
            clv = CustomerLifetimeValue(
                business_id=business_id,
                user_phone=user_phone
            )
            db.add(clv)
        
        # Calculate purchase metrics from completed carts
        purchase_stmt = select(
            func.count(Cart.id),
            func.sum(
                select(func.sum(CartItem.quantity * Product.price))
                .where(CartItem.cart_id == Cart.id)
                .join(Product, CartItem.product_id == Product.id)
                .correlate(Cart)
                .scalar_subquery()
            ),
            func.min(Cart.created_at),
            func.max(Cart.created_at)
        ).where(
            Cart.business_id == business_id,
            Cart.user_phone == user_phone,
            Cart.status.in_(["paid", "recovered"])
        )
        
        result = (await db.execute(purchase_stmt)).first()
        total_purchases = result[0] if result and result[0] else 0
        total_spent = float(result[1]) if result and result[1] else 0.0
        first_purchase = result[2]
        last_purchase = result[3]
        
        # Calculate abandoned/recovered carts
        abandoned = (await db.execute(
            select(func.count(Cart.id)).where(
                Cart.business_id == business_id,
                Cart.user_phone == user_phone,
                Cart.status == "abandoned"
            )
        )).scalar() or 0
        
        recovered = (await db.execute(
            select(func.count(Cart.id)).where(
                Cart.business_id == business_id,
                Cart.user_phone == user_phone,
                Cart.status == "recovered"
            )
        )).scalar() or 0
        
        # Update CLV record
        clv.total_purchases = total_purchases
        clv.total_spent = total_spent
        clv.avg_order_value = total_spent / total_purchases if total_purchases > 0 else 0
        clv.first_purchase_date = first_purchase
        clv.last_purchase_date = last_purchase
        clv.carts_abandoned = abandoned
        clv.carts_recovered = recovered
        clv.recovery_rate = (recovered / abandoned * 100) if abandoned > 0 else 0
        
        if last_purchase:
            clv.days_since_last_purchase = (datetime.utcnow() - last_purchase).days
            
            # Simple churn risk calculation
            if clv.days_since_last_purchase > 90:
                clv.churn_risk_score = 0.8  # High risk
            elif clv.days_since_last_purchase > 60:
                clv.churn_risk_score = 0.5  # Medium risk
            elif clv.days_since_last_purchase > 30:
                clv.churn_risk_score = 0.3  # Low-medium risk
            else:
                clv.churn_risk_score = 0.1  # Low risk
        
        await db.commit()
        logger.info(f"Updated CLV for {user_phone} in business {business_id}")
        
        return clv
    
    @classmethod
    async def get_clv_analytics(
        cls,
        db: AsyncSession,
        business_id: int,
        min_purchases: int = 0
    ) -> Dict:
        """
        Get aggregated CLV analytics for a business.
        
        Args:
            business_id: Business ID
            min_purchases: Minimum purchases to include in analysis
            
        Returns:
            Dict with avg CLV, total customers, segmentation, etc.
        """
        # Get all CLV records
        stmt = select(CustomerLifetimeValue).where(
            CustomerLifetimeValue.business_id == business_id,
            CustomerLifetimeValue.total_purchases >= min_purchases
        )
        
        clvs = (await db.execute(stmt)).scalars().all()
        
        if not clvs:
            return {
                "total_customers": 0,
                "avg_clv": 0,
                "avg_purchases_per_customer": 0,
                "avg_order_value": 0,
                "total_revenue": 0
            }
        
        total_customers = len(clvs)
        total_revenue = sum(c.total_spent for c in clvs)
        avg_clv = total_revenue / total_customers
        avg_purchases = sum(c.total_purchases for c in clvs) / total_customers
        avg_order_value = sum(c.avg_order_value for c in clvs) / total_customers
        
        # Segment customers
        high_value = [c for c in clvs if c.total_spent >= avg_clv * 2]
        medium_value = [c for c in clvs if avg_clv <= c.total_spent < avg_clv * 2]
        low_value = [c for c in clvs if c.total_spent < avg_clv]
        
        # Churn risk
        high_churn_risk = [c for c in clvs if c.churn_risk_score >= 0.7]
        
        return {
            "total_customers": total_customers,
            "total_revenue": round(total_revenue, 2),
            "avg_clv": round(avg_clv, 2),
            "avg_purchases_per_customer": round(avg_purchases, 2),
            "avg_order_value": round(avg_order_value, 2),
            "customer_segments": {
                "high_value": len(high_value),
                "medium_value": len(medium_value),
                "low_value": len(low_value)
            },
            "churn_risk": {
                "high_risk_customers": len(high_churn_risk),
                "percentage": round(len(high_churn_risk) / total_customers * 100, 2)
            }
        }
    
    # ============================================================================
    # AI PERFORMANCE METRICS
    # ============================================================================
    
    @classmethod
    async def get_ai_performance(
        cls,
        db: AsyncSession,
        business_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Analyze AI assistant performance.
        
        Returns:
            Dict with FAQ hit rate, AI usage, conversion rate, etc.
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Total interactions
        total_stmt = select(func.count(AIPerformanceMetric.id)).where(
            AIPerformanceMetric.business_id == business_id,
            AIPerformanceMetric.timestamp.between(start_date, end_date)
        )
        total_interactions = (await db.execute(total_stmt)).scalar() or 0
        
        if total_interactions == 0:
            return {"total_interactions": 0, "faq_hit_rate": 0, "ai_usage_rate": 0}
        
        # FAQ hits
        faq_stmt = select(func.count(AIPerformanceMetric.id)).where(
            AIPerformanceMetric.business_id == business_id,
            AIPerformanceMetric.response_source == 'faq',
            AIPerformanceMetric.timestamp.between(start_date, end_date)
        )
        faq_hits = (await db.execute(faq_stmt)).scalar() or 0
        
        # AI fallback usage
        ai_stmt = select(func.count(AIPerformanceMetric.id)).where(
            AIPerformanceMetric.business_id == business_id,
            AIPerformanceMetric.response_source == 'ai_fallback',
            AIPerformanceMetric.timestamp.between(start_date, end_date)
        )
        ai_usage = (await db.execute(ai_stmt)).scalar() or 0
        
        # Conversations that led to cart actions
        conversion_stmt = select(func.count(AIPerformanceMetric.id)).where(
            AIPerformanceMetric.business_id == business_id,
            AIPerformanceMetric.led_to_cart_action == True,
            AIPerformanceMetric.timestamp.between(start_date, end_date)
        )
        conversions = (await db.execute(conversion_stmt)).scalar() or 0
        
        # Average response time
        avg_time_stmt = select(func.avg(AIPerformanceMetric.response_time_ms)).where(
            AIPerformanceMetric.business_id == business_id,
            AIPerformanceMetric.timestamp.between(start_date, end_date),
            AIPerformanceMetric.response_time_ms.isnot(None)
        )
        avg_response_time = (await db.execute(avg_time_stmt)).scalar() or 0
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_interactions": total_interactions,
            "faq_hit_rate_percent": round(faq_hits / total_interactions * 100, 2),
            "ai_usage_rate_percent": round(ai_usage / total_interactions * 100, 2),
            "conversation_to_action_rate_percent": round(conversions / total_interactions * 100, 2),
            "avg_response_time_ms": round(avg_response_time, 2)
        }
