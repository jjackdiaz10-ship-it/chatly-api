
# app/models/bot_channel.py
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class BotChannel(Base):
    __tablename__ = "bot_channels"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="CASCADE"))
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"))

    bot = relationship("Bot", back_populates="channels")
    channel = relationship("Channel")  # solo lectura