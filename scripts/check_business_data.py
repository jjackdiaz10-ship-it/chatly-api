import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.base import Base
from app.db.session import AsyncSessionLocal
from app.models.business import Business
from app.models.business_user import BusinessUser
from app.models.subscription import Subscription
from app.models.plan import Plan

async def check_data():
    async with AsyncSessionLocal() as db:
        print("\n--- BUSINESSES ---")
        businesses = await db.execute(select(Business))
        for b in businesses.scalars().all():
            print(f"ID: {b.id} | Name: {b.name} | Code: {b.code}")

        print("\n--- BUSINESS USERS ---")
        busers = await db.execute(select(BusinessUser))
        for bu in busers.scalars().all():
            print(f"User {bu.user_id} -> Business {bu.business_id} (Role: {bu.role})")

        print("\n--- SUBSCRIPTIONS ---")
        subs = await db.execute(select(Subscription).options(selectinload(Subscription.plan)))
        for s in subs.scalars().all():
            pname = s.plan.name if s.plan else "None"
            print(f"ID: {s.id} | Business: {s.business_id} | Plan: {pname} | Active: {s.is_active}")

if __name__ == "__main__":
    asyncio.run(check_data())
