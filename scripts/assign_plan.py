# scripts/assign_plan.py
import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal
from app.models.subscription import Subscription
from app.models.plan import Plan
from sqlalchemy import select, update

async def assign_plan(business_id: int, plan_name: str, months: int = 1):
    async with AsyncSessionLocal() as db:
        # 1. Find the plan
        plan_res = await db.execute(select(Plan).where(Plan.name.ilike(f"%{plan_name}%")))
        plan = plan_res.scalars().first()
        
        if not plan:
            print(f"❌ Plan '{plan_name}' not found.")
            return

        # 2. Deactivate old ones
        await db.execute(
            update(Subscription)
            .where(Subscription.business_id == business_id)
            .values(is_active=False)
        )
        
        # 3. Create new
        new_sub = Subscription(
            business_id=business_id,
            plan_id=plan.id,
            billing_cycle="monthly" if months < 12 else "yearly",
            is_active=True,
            current_period_end=datetime.utcnow() + timedelta(days=30 * months)
        )
        
        db.add(new_sub)
        await db.commit()
        print(f"✅ Business {business_id} upgraded to {plan.name}!")
        print(f"📅 Expires on: {new_sub.current_period_end}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/assign_plan.py <business_id> <plan_name_fragment>")
        print("Example: python scripts/assign_plan.py 1 'Vantix Ultra'")
    else:
        bid = int(sys.argv[1])
        pname = sys.argv[2]
        asyncio.run(assign_plan(bid, pname))
