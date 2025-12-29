# app/schemas/bot_channel.py
from pydantic import BaseModel

class BotChannelCreate(BaseModel):
    bot_id: int
    channel_id: int

class BotChannelOut(BaseModel):
    id: int
    bot_id: int
    channel_id: int

    class Config:
        from_attributes = True