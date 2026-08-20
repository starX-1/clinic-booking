import asyncio
from app.core.database import Base, engine
import app.models  # Load metadata


async def reset():
    print("Dropping existing tables in Neon DB...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Successfully reset tables in Neon DB!")



if __name__ == "__main__":
    asyncio.run(reset())
