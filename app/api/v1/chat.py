# app/api/v1/chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.bot import Bot
from app.models.ecommerce_config import EcommerceConfig
from app.services.ai_service import AIService
from app.services.rule_engine import RuleEngine
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/chat", tags=["Chat"])

class WidgetConfig(BaseModel):
    business_id: int
    color: str
    welcome_message: str
    position: str

class ChatRequest(BaseModel):
    business_id: int
    message: str
    history: List[dict] = []

@router.get("/widget-config/{business_id}", response_model=WidgetConfig)
async def get_widget_config(business_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(EcommerceConfig).where(EcommerceConfig.business_id == business_id)
    )
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Widget config not found")
        
    s = config.widget_settings or {}
    return {
        "business_id": business_id,
        "color": s.get("color", "#007bff"),
        "welcome_message": s.get("welcome_message", "Holi! ¿Cómo te ayudo?"),
        "position": s.get("position", "bottom-right")
    }

@router.post("/message")
async def chat_message(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    # 1. Find an active bot for this business
    bot_res = await db.execute(
        select(Bot).where(Bot.business_id == req.business_id, Bot.is_active == True)
    )
    bot = bot_res.scalars().first()
    if not bot:
        raise HTTPException(status_code=404, detail="No active bot for this business")
        
    response_text = None
    
    # 2. Rule Engine
    if bot.hybrid_mode and bot.rule_set:
        response_text = RuleEngine.match(req.message, bot.rule_set)
        
    # 3. AI Fallback
    if not response_text and "gemini_api_key" in bot.config:
        ai = AIService(bot.config["gemini_api_key"])
        response_text = await ai.chat(db, bot.business_id, req.message, req.history)
        
    if not response_text:
        response_text = "Lo siento, no pude procesar tu mensaje."
        
    return {"message": response_text}
