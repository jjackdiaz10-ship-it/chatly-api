from app.core.crud_factory import generate_crud
from app.models.business_user import BusinessUser
from app.schemas.business_user import BusinessUserCreate, BusinessUserUpdate

router = generate_crud(
    model=BusinessUser,
    schema_create=BusinessUserCreate,
    schema_update=BusinessUserUpdate,
    prefix="/business_users",
    tag="Business Users",
    permissions={
        "create": "businessusers:create",
        "read": "businessusers:view",
        "update": "businessusers:update",
        "delete": "businessusers:delete"
    }
)
