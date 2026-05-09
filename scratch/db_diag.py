import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import get_settings
import psycopg
from psycopg_pool import AsyncConnectionPool

async def diagnose():
    settings = get_settings()
    print(f"Testing connection to: {settings.DATABASE_URL}")
    
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("Set WindowsSelectorEventLoopPolicy")

    # 1. Direct connection
    try:
        async with await psycopg.AsyncConnection.connect(settings.DATABASE_URL) as conn:
            print("Direct connection successful!")
            res = await conn.execute("SELECT version()")
            row = await res.fetchone()
            print(f"Postgres Version: {row[0]}")
    except Exception as e:
        print(f"Direct connection FAILED: {e}")
        return

    # 2. Pool connection
    try:
        print("Initializing pool...")
        async with AsyncConnectionPool(conninfo=settings.DATABASE_URL, min_size=0, max_size=5) as pool:
            print("Pool initialized. Waiting for connection...")
            async with pool.connection() as conn:
                print("Connection from pool successful!")
                res = await conn.execute("SELECT 1")
                row = await res.fetchone()
                print(f"Query Result: {row[0]}")
    except Exception as e:
        print(f"Pool connection FAILED: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("Set WindowsSelectorEventLoopPolicy")
    asyncio.run(diagnose())
