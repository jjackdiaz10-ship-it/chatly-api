# app/api/v1/bot_channels.py
from app.core.crud_factory import generate_crud
from app.models.bot_channel import BotChannel
from app.schemas.bot_channel import BotChannelCreate, BotChannelOut

router = generate_crud(
    model=BotChannel,
    schema_create=BotChannelCreate,
    schema_update=BotChannelCreate,  # opcional, solo para edición
    prefix="/bot-channels",
    tag="Bot Channels",
    permissions={
        "create": "botchannels:create",
        "read": "botchannels:view",
        "update": "botchannels:update",
        "delete": "botchannels:delete"
    }
)