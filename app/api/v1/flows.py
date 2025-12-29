# app/api/v1/flows.py
from app.core.crud_factory import generate_crud
from app.models.flow import Flow
from app.schemas.flow import FlowCreate, FlowUpdate

router = generate_crud(
    model=Flow,
    schema_create=FlowCreate,
    schema_update=FlowUpdate,
    prefix="/flows",
    tag="Flows",
    permissions={
        "create": "flows:create",
        "read": "flows:view",
        "update": "flows:update",
        "delete": "flows:delete"
    }
)
