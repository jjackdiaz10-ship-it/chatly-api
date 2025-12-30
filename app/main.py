from fastapi import FastAPI, APIRouter
from app.core.permissions_setup import generate_permissions
from app.db.session import AsyncSessionLocal
from app.api.v1.auth import router as auth_router
from app.api.v1.channels import router as channels_router
from app.api.v1.users import router as users_router
from app.api.v1.roles import router as roles_router
from app.api.v1.businesses import router as businesses_router
from app.api.v1.business_users import router as business_users_router
from app.api.v1.business_channels import router as business_channels_router
from app.api.v1.categories import router as categories_router
from app.api.v1.products import router as products_router
from app.api.v1.permissions import router as permissions_router
from app.api.v1.bots import router as bots_router
from app.api.v1.bot_channels import router as bot_channels_router
from app.api.v1.role_permissions import router as role_permissions_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.flows import router as flows_router
from app.api.v1.ecommerce_configs import router as ecommerce_configs_router
from app.api.v1.payment_configs import router as payment_configs_router
from app.api.v1.chat import router as chat_router
from app.api.v1.widget import router as widget_router
from app.api.v1.ecommerce import router as ecommerce_router
from app.api.v1.payments import router as payments_router
from app.api.v1.carts import router as carts_router
from app.api.v1.knowledge_base import router as kb_router
from app.api.v1.plans import router as plans_router
from app.api.v1.admin import router as admin_router
from app.models import Role, Permission, User, Business, BusinessUser, BusinessChannel, Category, Product

app = FastAPI(
    title="Chatly API",
    version="1.0.0"
)

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_router)
v1_router.include_router(channels_router)
v1_router.include_router(users_router)
v1_router.include_router(roles_router)
v1_router.include_router(businesses_router)
v1_router.include_router(business_users_router)
v1_router.include_router(business_channels_router)
v1_router.include_router(categories_router)
v1_router.include_router(products_router)
v1_router.include_router(permissions_router)
v1_router.include_router(bots_router)
v1_router.include_router(bot_channels_router)
v1_router.include_router(role_permissions_router)
v1_router.include_router(webhooks_router)
v1_router.include_router(flows_router)
v1_router.include_router(ecommerce_configs_router)
v1_router.include_router(payment_configs_router)
v1_router.include_router(chat_router)
v1_router.include_router(widget_router)
v1_router.include_router(ecommerce_router)
v1_router.include_router(payments_router)
v1_router.include_router(carts_router)
v1_router.include_router(kb_router)
v1_router.include_router(plans_router)
v1_router.include_router(admin_router)

app.include_router(v1_router)

# @app.on_event("startup")
# async def startup_event():
#     async with AsyncSessionLocal() as db:
#         await generate_permissions(db)