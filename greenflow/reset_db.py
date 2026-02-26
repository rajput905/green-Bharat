import sys
from pathlib import Path

# Add current directory to path to allow running from parent dir
curr_dir = Path(__file__).parent.absolute()
if str(curr_dir) not in sys.path:
    sys.path.insert(0, str(curr_dir))

import asyncio
from database.session import engine, Base

async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database reset successfully.")

if __name__ == "__main__":
    asyncio.run(reset_db())
