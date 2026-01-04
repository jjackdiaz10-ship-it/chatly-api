import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.business_user import BusinessUser

async def force_link():
    async with AsyncSessionLocal() as db:
        print("Checking for existing link (User 1 -> Business 1)...")
        result = await db.execute(select(BusinessUser).where(BusinessUser.user_id == 1, BusinessUser.business_id == 1))
        link = result.scalar_one_or_none()
        
        if link:
            print(f"Link FOUND: ID={link.id}, Active={link.is_active}, Role={link.role}")
            if not link.is_active:
                print("Link is inactive. Reactivating...")
                link.is_active = True
                await db.commit()
                print("Reactivated.")
        else:
            print("Link NOT found. Creating...")
            link = BusinessUser(
                user_id=1,
                business_id=1,
                role="Owner",
                is_active=True
            )
            db.add(link)
            await db.commit()
            print("CREATED Link User 1 -> Business 1 (Poleras)")

if __name__ == "__main__":
    asyncio.run(force_link())
