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
        if "object" in data and data["object"] == "whatsapp_business_account":
            for entry in data["entry"]:
                for change in entry["changes"]:
                    value = change["value"]
                    if "messages" in value:
                        for msg in value["messages"]:
                            from_num = msg["from"]
                            text = msg.get("text", {}).get("body")
                            # Handle interactive responses (button/list clicks)
                            if "interactive" in msg:
                                i_type = msg["interactive"]["type"]
                                if i_type == "button_reply":
                                    text = msg["interactive"]["button_reply"]["title"]
                                elif i_type == "list_reply":
                                    text = msg["interactive"]["list_reply"]["title"]
                                    # Could also use ID if needed: msg["interactive"]["list_reply"]["id"]
                                    
                            print(f"DEBUG: Received message from {from_num}: {text}")
                            if not text:
                                continue
                                
                            phone_id = value["metadata"]["phone_number_id"]
                            
                            # Find Bot assigned to this channel
                            bot_res = await db.execute(
                                select(Bot)
                                .join(BotChannel)
                                .where(BotChannel.business_channel_id == business_channel_id)
                            )
                            bot = bot_res.scalars().first()
                            
                            if bot and bot.is_active:
                                response_content = None
                                msg_type = "text"
                                print(f"DEBUG: Found active bot: {bot.name}")
                                
                                # 1. Native Mastermind AI
                                print("DEBUG: Using Mastermind Native Sales AI...")
                                ai = AIService(bot)
                                response_content, msg_type = await ai.chat(db, bot.business_id, from_num, text)
                                print(f"DEBUG: AI Response ({msg_type}): {response_content}")
                                
                                # 2. Send
                                if response_content:
                                    print(f"DEBUG: Attempting to send message to {from_num}")
                                    try:
                                        meta = MetaService(channel.token, phone_id)
                                        send_res = await meta.send_whatsapp_message(from_num, response_content, msg_type)
                                        print(f"DEBUG: Meta send response: {send_res}")
                                    except Exception as e:
                                        print(f"DEBUG: Exception during Meta send: {str(e)}")
                                else:
                                    print("DEBUG: No response content generated")
                                else:
                                    logging.warning("No response text generated")
                            else:
                                logging.warning(f"No active bot found for channel {business_channel_id}")
                                
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Error processing webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
