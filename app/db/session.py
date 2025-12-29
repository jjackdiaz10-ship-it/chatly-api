from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

import os
from dotenv import load_dotenv

load_dotenv()

# Use the environment variable if available (e.g., on Render), otherwise fall back to local dev DB
# Note: Render provides an internal URL (dpg-...) which is only accessible from within Render.
# For local development, use your local Postgres or the 'External Database URL' from Render.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://chatly:rETMFt1WvJRakzLoUeRQ83P6dhbINHKo@dpg-d58u39qli9vc73a9micg-a.oregon-postgres.render.com/chatly_rg15"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
