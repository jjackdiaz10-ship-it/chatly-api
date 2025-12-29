from app.core.crud_factory import generate_crud
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate

router = generate_crud(
    model=Role,
    schema_create=RoleCreate,
    schema_update=RoleUpdate,
    prefix="/roles",
    tag="Roles",
    permissions={
        "create": "roles:create",
        "read": "roles:view",
        "update": "roles:update",
        "delete": "roles:delete"
    }
)
