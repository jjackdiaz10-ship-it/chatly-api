from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.permission import Permission

MODELS_PERMISSIONS = {
    # System Core
    "Users": ["create", "view", "update", "delete"],
    "Roles": ["create", "view", "update", "delete"],
    "Permissions": ["create", "view", "update", "delete"],
    
    # Business Core
    "Businesses": ["create", "view", "update", "delete"],
    "BusinessUsers": ["create", "view", "update", "delete"],
    
    # Messaging Channels
    "Channels": ["create", "view", "update", "delete"],
    "BusinessChannels": ["create", "view", "update", "delete"],
    
    # Bots & Automation
    "Bots": ["create", "view", "update", "delete"],
    "BotChannels": ["create", "view", "update", "delete"],
    "Flows": ["create", "view", "update", "delete"],
    
    # Ecommerce
    "Categories": ["create", "view", "update", "delete"],
    "Products": ["create", "view", "update", "delete"],
    "EcommerceConfigs": ["create", "view", "update", "delete"],
    "BusinessCategories": ["create", "view", "update", "delete"],
    "BusinessProducts": ["create", "view", "update", "delete"],
    
    # Payments
    "Payments": ["create", "view", "update", "delete"],
    "PaymentConfigs": ["create", "view", "update", "delete"],
    
    # Widget
    "Widgets": ["create", "view", "update", "delete"],
    
    # Specific specialized permissions if needed
    "Chat": ["view", "interact"],
    "Webhooks": ["view", "manage"],
}


async def generate_permissions(db: AsyncSession):
    for model_name, actions in MODELS_PERMISSIONS.items():
        for action in actions:
            code = f"{model_name.lower()}:{action}"
            # Check if exists
            result = await db.execute(select(Permission).where(Permission.code == code))
            perm = result.scalar_one_or_none()
            if not perm:
                db.add(Permission(code=code))
    await db.commit()