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
            await db.refresh(user)

        # 3. Create Default Business if not exists
        from app.models.business import Business
        from app.models.business_user import BusinessUser

        result = await db.execute(select(Business).where(Business.code == "default"))
        business = result.scalar_one_or_none()
        
        if not business:
            business = Business(
                code="default",
                name="Chatly Default Shop",
                is_active=True
            )
            db.add(business)
            await db.commit()
            await db.refresh(business)
        
        # 4. Link User to Business
        result = await db.execute(select(BusinessUser).where(BusinessUser.user_id == user.id, BusinessUser.business_id == business.id))
        link = result.scalar_one_or_none()
        
        if not link:
            link = BusinessUser(
                user_id=user.id,
                business_id=business.id,
                role="Owner",
                is_active=True
            )
            db.add(link)
            await db.commit()
            print(f"Admin user linked to business: {business.name}")

if __name__ == "__main__":
    asyncio.run(create_admin())
