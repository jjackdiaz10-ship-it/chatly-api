import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.business_channel import BusinessChannel
from app.models.bot_channel import BotChannel
from app.models.bot import Bot
from app.models.product import Product
from app.models.cart import Cart
import app.models

async def check_health():
    print("--- CHATLY MASTERMIND HEALTH CHECK ---\n")
    async with AsyncSessionLocal() as db:
        # 1. Check DB Connectivity
        try:
            await db.execute(select(1))
            print("[OK] Database connection successful.")
        except Exception as e:
            print(f"[FAIL] Database connection failed: {e}")
            return

        # 2. Check Tables Existence (Migration check)
        try:
            await db.execute(select(Cart).limit(1))
            print("[OK] Cart table exists (Migrations applied).")
        except Exception as e:
            print(f"[FAIL] Cart table not found. Did you run 'alembic upgrade head'?")

        # 3. Check Channel & Token
        res = await db.execute(select(BusinessChannel))
        channels = res.scalars().all()
        if not channels:
            print("[FAIL] No BusinessChannels found. You need to create one.")
        else:
            for c in channels:
                print(f"[INFO] Channel ID {c.id}: Active={c.active}, Token Present={'Yes' if c.token else 'No'}")
                if not c.token:
                    print(f"       -> WARNING: Channel {c.id} has no Access Token.")

        # 4. Check Bot-Channel Linking
        bot_links = await db.execute(select(BotChannel))
        links = bot_links.scalars().all()
        if not links:
            print("[FAIL] No Bot-Channel links found. Run 'python link_bot.py' to link a bot to your channel.")
        else:
            for l in links:
                print(f"[OK] Bot ID {l.bot_id} linked to BusinessChannel ID {l.business_channel_id}.")

        # 5. Check Products
        prod_res = await db.execute(select(Product))
        prods = prod_res.scalars().all()
        print(f"[INFO] Products in database: {len(prods)}")
        if not any(p.stock > 0 for p in prods):
            print("[WARNING] All products have 0 stock. The Mastermind AI will not show them in the catalog.")

    print("\nHealth check complete.")

if __name__ == "__main__":
    asyncio.run(check_health())
