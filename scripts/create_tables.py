# scripts/create_tables.py
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from app.db.base_class import Base
import app.models # Ensure all models are loaded

async def create_tables():
    async with engine.begin() as conn:
        # This will create tables that don't exist
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())
