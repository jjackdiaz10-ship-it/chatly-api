# app/api/v1/analytics.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from pydantic import BaseModel

router = APIRouter(prefix="/analytics", tags=["Analytics"])

class DateRangeParams(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

@router.get("/cart-recovery/{business_id}")
async def get_cart_recovery_metrics(
    business_id: int,
    start_date: Optional[str] = Query(None, description="ISO format: 2024-01-01T00:00:00"),
    end_date: Optional[str] = Query(None, description="ISO format: 2024-01-31T23:59:59"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get cart recovery performance metrics.
    
    Returns:
    - Total abandoned carts
    - Recovery rate
    - Revenue from recovered carts
    - Average time to recovery
    """
    # Parse dates
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    metrics = await AnalyticsService.get_cart_recovery_metrics(
        db=db,
        business_id=business_id,
        start_date=start,
        end_date=end
    )
    
    return metrics

@router.get("/clv/{business_id}")
async def get_clv_analytics(
    business_id: int,
    min_purchases: int = Query(0, description="Minimum purchases to include"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get Customer Lifetime Value analytics.
    
    Returns:
    - Average CLV
    - Total customers
    - Customer segmentation (high/medium/low value)
    - Churn risk analysis
    """
    analytics = await AnalyticsService.get_clv_analytics(
        db=db,
        business_id=business_id,
        min_purchases=min_purchases
    )
    
    return analytics

@router.get("/ai-performance/{business_id}")
async def get_ai_performance(
    business_id: int,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get AI assistant performance metrics.
    
    Returns:
    - FAQ hit rate
    - AI fallback usage rate
    - Conversation-to-action conversion rate
    - Average response time
    """
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    performance = await AnalyticsService.get_ai_performance(
        db=db,
        business_id=business_id,
        start_date=start,
        end_date=end
    )
    
    return performance

@router.get("/dashboard/{business_id}")
async def get_analytics_dashboard(
    business_id: int,
    days: int = Query(30, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive analytics dashboard with all metrics.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Fetch all metrics in parallel
    cart_recovery = await AnalyticsService.get_cart_recovery_metrics(
        db, business_id, start_date, end_date
    )
    clv = await AnalyticsService.get_clv_analytics(db, business_id)
    ai_performance = await AnalyticsService.get_ai_performance(
        db, business_id, start_date, end_date
    )
    
    return {
        "business_id": business_id,
        "period_days": days,
        "cart_recovery": cart_recovery,
        "customer_lifetime_value": clv,
        "ai_performance": ai_performance
    }

@router.post("/clv/update/{business_id}/{user_phone}")
async def update_customer_clv(
    business_id: int,
    user_phone: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger CLV recalculation for a specific customer.
    Useful after major purchases or to refresh stale data.
    """
    clv = await AnalyticsService.update_customer_clv(
        db=db,
        business_id=business_id,
        user_phone=user_phone
    )
    
    return {
        "user_phone": user_phone,
        "business_id": business_id,
        "total_purchases": clv.total_purchases,
        "total_spent": clv.total_spent,
        "avg_order_value": clv.avg_order_value,
        "churn_risk_score": clv.churn_risk_score
    }
