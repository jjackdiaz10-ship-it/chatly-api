# app/api/v1/webhooks.py
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.bot import Bot
from app.services.ai_service import AIService
from app.services.meta_service import MetaService
from app.services.payment_service import PaymentService
from app.models.payment_config import PaymentConfig
from app.models.business_channel import BusinessChannel
from app.models.bot_channel import BotChannel
from sqlalchemy import select
import logging
import re

from fastapi.responses import PlainTextResponse
import os

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.get("/{channel_name}/{business_channel_id}")
async def verify_webhook_by_id(channel_name: str, business_channel_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(BusinessChannel).where(BusinessChannel.id == business_channel_id))
    channel = res.scalars().first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    params = request.query_params
    
    # 1. Try to get token from channel metadata
    # 2. Fallback to ENV variable
    # 3. Default fallback
    verify_token = channel.metadata_json.get("verify_token") or os.getenv("WEBHOOK_VERIFY_TOKEN", "chatly_verify_token")
    
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == verify_token:
        challenge = params.get("hub.challenge")
        return PlainTextResponse(content=challenge)
        
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@router.post("/{channel_name}/{business_channel_id}")
async def handle_webhook_by_id(channel_name: str, business_channel_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    # Here we would verify X-Hub-Signature against channel.token (if it's the app secret)
    # For now implementation focuses on routing logic
    res = await db.execute(select(BusinessChannel).where(BusinessChannel.id == business_channel_id))
    channel = res.scalars().first()
    
    if not channel or not channel.active:
        raise HTTPException(status_code=404, detail="Channel not active")

    data = await request.json()
    logging.info(f"Webhook received: {data}")
    
    try:
        # 1. WHATSAPP ENGINE
        if "object" in data and data["object"] == "whatsapp_business_account":
            for entry in data["entry"]:
                for change in entry["changes"]:
                    value = change["value"]
                    if "messages" in value:
                        for msg in value["messages"]:
                            from_num = msg["from"]
                            text = _extract_text(msg)
                            if not text: continue
                                                
                            phone_id = value["metadata"]["phone_number_id"]
                            bot = await _get_bot_for_channel(db, business_channel_id)
                            
                            if bot and bot.is_active:
                                response_content, msg_type = await AIService(bot).chat(db, bot.business_id, from_num, text)
                                if response_content:
                                    meta = MetaService(channel.token, phone_id)
                                    await meta.send_whatsapp_message(from_num, response_content, msg_type)

        # 2. INSTAGRAM / MESSENGER ENGINE
        elif "object" in data and data["object"] == "instagram":
            for entry in data["entry"]:
                for messaging in entry.get("messaging", []):
                    sender_id = messaging["sender"]["id"]
                    text = messaging.get("message", {}).get("text")
                    if not text: continue
                    
                    bot = await _get_bot_for_channel(db, business_channel_id)
                    if bot and bot.is_active:
                        # AIService treats sender_id as the unique contact identifier (agnostic)
                        response_content, msg_type = await AIService(bot).chat(db, bot.business_id, sender_id, text)
                        if response_content:
                            meta = MetaService(channel.token)
                            await meta.send_instagram_message(sender_id, response_content, msg_type)

        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Error processing webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

async def _get_bot_for_channel(db, business_channel_id):
    bot_res = await db.execute(
        select(Bot)
        .join(BotChannel)
        .where(BotChannel.business_channel_id == business_channel_id)
    )
    return bot_res.scalars().first()

def _extract_text(msg):
    text = msg.get("text", {}).get("body")
    if "interactive" in msg:
        i_type = msg["interactive"]["type"]
        if i_type == "button_reply":
            text = msg["interactive"]["button_reply"]["title"]
        elif i_type == "list_reply":
            text = msg["interactive"]["list_reply"]["title"]
    return text
