# scripts/seed_plans.py
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal
from app.models.plan import Plan
import app.models
from sqlalchemy import select

async def seed_plans():
    plans = [
        {
            "name": "Vantix Core (Standard)",
            "price_monthly": 355.0,
            "price_yearly": 3195.0, # ~25% disc
            "max_conversations": 3000,
            "max_users": 5,
            "max_funnels": 1,
            "features": {"ai_model": "Gemini 2.5 Flash", "api_access": True, "integrations": "standard"}
        },
        {
            "name": "Vantix Ultra (Advanced)",
            "price_monthly": 539.0,
            "price_yearly": 4850.0,
            "max_conversations": 10000,
            "max_users": 10,
            "max_funnels": 2,
            "features": {"ai_model": "Gemini 2.5 Flash", "ads": True, "phone": True, "gmail_addon": True}
        },
        {
            "name": "Vantix Prime (Expert)",
            "price_monthly": 794.0,
            "price_yearly": 7146.0,
            "max_conversations": 50000,
            "max_users": 999,
            "max_funnels": 3,
            "features": {"vambe_axis": True, "instagram_ai": True, "consultancy": True, "engineer_support": True}
        },
        {
            "name": "Vantix Iris (Lite)",
            "price_monthly": 19.0,
            "price_yearly": 190.0,
            "max_conversations": 1000,
            "max_users": 1,
            "max_funnels": 1,
            "features": {"basic_support": True, "templates": True}
        }
    ]

    async with AsyncSessionLocal() as db:
        for p_data in plans:
            # Check if exists
            stmt = select(Plan).where(Plan.name == p_data["name"])
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not existing:
                plan = Plan(**p_data)
                db.add(plan)
        
        await db.commit()
        print("✅ Plans seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_plans())
