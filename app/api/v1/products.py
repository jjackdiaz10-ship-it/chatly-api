from app.core.crud_factory import generate_crud
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate

router = generate_crud(
    model=Product,
    schema_create=ProductCreate,
    schema_update=ProductUpdate,
    prefix="/products",
    tag="Products",
    permissions={
        "create": "products:create",
        "read": "products:view",
        "update": "products:update",
        "delete": "products:delete"
    }
)
