from app.core.crud_factory import generate_crud
from app.models.business_channel import BusinessChannel
from app.schemas.business_channel import BusinessChannelCreate, BusinessChannelUpdate

router = generate_crud(
    model=BusinessChannel,
    schema_create=BusinessChannelCreate,
    schema_update=BusinessChannelUpdate,
    prefix="/business_channels",
    tag="Business Channels",
    permissions={
        "create": "businesschannels:create",
        "read": "businesschannels:view",
        "update": "businesschannels:update",
        "delete": "businesschannels:delete"
    }
)
