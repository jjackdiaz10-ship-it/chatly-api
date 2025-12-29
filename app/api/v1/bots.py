# app/api/v1/bots.py
from app.core.crud_factory import generate_crud
from app.models.bot import Bot
from app.schemas.bot import BotCreate, BotUpdate

router = generate_crud(
    model=Bot,
    schema_create=BotCreate,
    schema_update=BotUpdate,
    prefix="/bots",
    tag="Bots",
    permissions={
        "create": "bots:create",
        "read": "bots:view",
        "update": "bots:update",
        "delete": "bots:delete"
    }
)