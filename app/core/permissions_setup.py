# app/core/permissions_setup.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.permission import Permission

# app/core/permissions_setup.py
MODELS_PERMISSIONS = {
    "Users": ["create", "view", "update", "delete"],
    "Roles": ["create", "view", "update", "delete"],
    "Permissions": ["create", "view", "update", "delete"],
    "Channels": ["create", "view", "update", "delete"],
    "Bots": ["create", "view", "update", "delete"],
    "BotChannels": ["create", "view", "update", "delete"],
    "Categories": ["create", "view", "update", "delete"],
    "Products": ["create", "view", "update", "delete"],
    "Businesses": ["create", "view", "update", "delete"],
    "BusinessUsers": ["create", "view", "update", "delete"],
    "BusinessChannels": ["create", "view", "update", "delete"],
    "BusinessBots": ["create", "view", "update", "delete"],
    "BusinessCategories": ["create", "view", "update", "delete"],
    "BusinessProducts": ["create", "view", "update", "delete"],
}


async def generate_permissions(db: AsyncSession):
    for model_name, actions in MODELS_PERMISSIONS.items():
        for action in actions:
            code = f"{model_name.lower()}:{action}"
            result = await db.execute(select(Permission).where(Permission.code == code))
            perm = result.scalar_one_or_none()
            if not perm:
                db.add(Permission(code=code))
    await db.commit()