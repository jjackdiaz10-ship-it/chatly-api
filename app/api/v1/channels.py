from app.core.crud_factory import generate_crud
from app.models.channel import Channel
from app.schemas.channel import ChannelCreate, ChannelUpdate

router = generate_crud(
    model=Channel,
    schema_create=ChannelCreate,
    schema_update=ChannelUpdate,
    prefix="/channels",
    tag="Channels",
    permissions={
        "create": "channels:create",
        "read": "channels:view",
        "update": "channels:update",
        "delete": "channels:delete"
    }
)
