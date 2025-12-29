# app/api/v1/payment_configs.py
from app.core.crud_factory import generate_crud
from app.models.payment_config import PaymentConfig
from app.schemas.payment_config import PaymentConfigCreate, PaymentConfigUpdate

router = generate_crud(
    model=PaymentConfig,
    schema_create=PaymentConfigCreate,
    schema_update=PaymentConfigUpdate,
    prefix="/payment-configs",
    tag="Payment Configs",
    permissions={
        "create": "payments:manage",
        "read": "payments:view",
        "update": "payments:manage",
        "delete": "payments:manage"
    }
)
