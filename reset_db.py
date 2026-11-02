import asyncio
from sqlalchemy import text
from backend.database import engine, Base

async def reset_db():
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
        # Recreate all tables
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database schema reset successfully")

if __name__ == "__main__":
    asyncio.run(reset_db())
