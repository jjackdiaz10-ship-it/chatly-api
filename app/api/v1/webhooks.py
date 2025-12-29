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
                            print(f"DEBUG: Received message from {from_num}: {text}")
                            if not text:
                                continue
                                
                            phone_id = value["metadata"]["phone_number_id"]
                            logging.info(f"Message from {from_num}: {text}")
                            
                            # Find Bot assigned to this channel
                            bot_res = await db.execute(
                                select(Bot)
                                .join(BotChannel)
                                .where(BotChannel.business_channel_id == business_channel_id)
                            )
                            bot = bot_res.scalars().first()
                            
                            if bot and bot.is_active:
                                response_text = None
                                print(f"DEBUG: Found active bot: {bot.name}")
                                
                                # 1. Hybrid Rule Engine
                                if bot.hybrid_mode and bot.rule_set:
                                    from app.services.rule_engine import RuleEngine
                                    response_text = RuleEngine.match(text, bot.rule_set)
                                    if response_text:
                                        logging.info(f"Rule match: {response_text}")
                                
                                # 2. Native AI Fallback
                                if not response_text:
                                    logging.info("Using Native Sales AI...")
                                    ai = AIService()
                                    response_text = await ai.chat(db, bot.business_id, text)
                                    logging.info(f"Native AI Response: {response_text}")
                                    
                                    # 3. Payment Links
                                    if response_text and "[PAYLINK:" in response_text:
                                        pc_res = await db.execute(
                                            select(PaymentConfig).where(PaymentConfig.business_id == bot.business_id, PaymentConfig.active == True)
                                        )
                                        p_config = pc_res.scalars().first()
                                        if p_config:
                                            matches = re.findall(r"\[PAYLINK:(\d+)\]", response_text)
                                            for pid in matches:
                                                link = PaymentService.generate_payment_link(
                                                    p_config.provider, p_config.credentials, int(pid), 0.0
                                                )
                                                response_text = response_text.replace(f"[PAYLINK:{pid}]", link)
                                
                                # 4. Send
                                if response_text:
                                    print(f"DEBUG: Sending message to {from_num}: {response_text}")
                                    meta = MetaService(channel.token, phone_id)
                                    send_res = await meta.send_whatsapp_message(from_num, response_text)
                                    print(f"DEBUG: Meta send response: {send_res}")
                                else:
                                    logging.warning("No response text generated")
                            else:
                                logging.warning(f"No active bot found for channel {business_channel_id}")
                                
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Error processing webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
