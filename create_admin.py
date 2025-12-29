import asyncio
from sqlalchemy import select

from app.db.base import Base  # 👈 CLAVE
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.role import Role
from app.core.security import hash_password

async def create_admin():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Role).where(Role.name == "Admin"))
        role = result.scalar_one_or_none()

        if not role:
            role = Role(name="Admin")
            db.add(role)
            await db.commit()
            await db.refresh(role)

        result = await db.execute(select(User).where(User.email == "admin@admin.com"))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email="admin@admin.com",
                password=hash_password("12345"),
                role_id=role.id,
                is_active=True
            )
            db.add(user)
            await db.commit()

if __name__ == "__main__":
    asyncio.run(create_admin())
