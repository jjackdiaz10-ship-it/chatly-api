from app.core.crud_factory import generate_crud
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate

router = generate_crud(
    model=Category,
    schema_create=CategoryCreate,
    schema_update=CategoryUpdate,
    prefix="/categories",
    tag="Categories",
    permissions={
        "create": "categories:create",
        "read": "categories:view",
        "update": "categories:update",
        "delete": "categories:delete"
    }
)
