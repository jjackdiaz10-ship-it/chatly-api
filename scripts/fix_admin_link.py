import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.business_user import BusinessUser

async def fix_link():
    async with AsyncSessionLocal() as db:
        # Link User 1 to Business 1 (Poleras)
        result = await db.execute(select(BusinessUser).where(BusinessUser.user_id == 1, BusinessUser.business_id == 1))
        link = result.scalar_one_or_none()
        
        if not link:
            link = BusinessUser(
                user_id=1,
                business_id=1,
                role="Owner",
                is_active=True
            )
            db.add(link)
            await db.commit()
            print("Successfully linked User 1 to Business 1 (Poleras)")
        else:
            print("Link already exists")

if __name__ == "__main__":
    asyncio.run(fix_link())
