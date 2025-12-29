# app/api/v1/widget.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.widget_config import WidgetConfig
from app.schemas.widget_config import WidgetConfigOut, WidgetConfigUpdate, WidgetConfigCreate

router = APIRouter(prefix="/widget", tags=["Widget"])

@router.get("/config/{business_id}", response_model=WidgetConfigOut)
async def get_widget_config(business_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(WidgetConfig).where(WidgetConfig.business_id == business_id)
    )
    config = res.scalars().first()
    if not config:
        # Return default config if none exists
        return WidgetConfigOut(
            id=0,
            business_id=business_id,
            color="#8b5cf6",
            position="bottom-right",
            welcome_message="¡Hola! ¿En qué puedo ayudarte?"
        )
    return config

@router.put("/config/{business_id}", response_model=WidgetConfigOut)
async def update_widget_config(business_id: int, data: WidgetConfigUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(WidgetConfig).where(WidgetConfig.business_id == business_id)
    )
    config = res.scalars().first()
    
    if not config:
        # Create new config
        config = WidgetConfig(
            business_id=business_id,
            color=data.color or "#8b5cf6",
            position=data.position or "bottom-right",
            welcome_message=data.welcome_message or "¡Hola! ¿En qué puedo ayudarte?"
        )
        db.add(config)
    else:
        # Update existing
        if data.color is not None:
            config.color = data.color
        if data.position is not None:
            config.position = data.position
        if data.welcome_message is not None:
            config.welcome_message = data.welcome_message
    
    await db.commit()
    await db.refresh(config)
    return config
