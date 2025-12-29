from app.core.crud_factory import generate_crud
from app.models.business import Business
from app.schemas.business import BusinessCreate, BusinessUpdate

router = generate_crud(
    model=Business,
    schema_create=BusinessCreate,
    schema_update=BusinessUpdate,
    prefix="/businesses",
    tag="Businesses",
    permissions={
        "create": "businesses:create",
        "read": "businesses:view",
        "update": "businesses:update",
        "delete": "businesses:delete"
    }
)
