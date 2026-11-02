import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from database import AsyncSessionLocal
from routers.reviews import scan_all_reviews

async def debug_scan():
    print("Debugging scan_all_reviews...")
    async with AsyncSessionLocal() as db:
        try:
            # Call scan logic directly
            result = await scan_all_reviews(db)
            print(f"Success: {result}")
        except Exception as e:
            print(f"Caught Exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # We might need to mock some FastAPI things if they are used as depends
    # but here we just pass the db directly.
    asyncio.run(debug_scan())
