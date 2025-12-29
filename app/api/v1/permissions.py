from app.core.crud_factory import generate_crud
from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate

router = generate_crud(
    model=Permission,
    schema_create=PermissionCreate,
    schema_update=PermissionUpdate,
    prefix="/permissions",
    tag="Permissions",
    permissions={
        "create": "permissions:create",
        "read": "permissions:view",
        "update": "permissions:update",
        "delete": "permissions:delete"
    }
)
