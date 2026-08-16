"""Fix: adds SUCCESS value to insighttype enum in PostgreSQL."""
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        host='localhost', port=5432,
        user='postgres', password='bristi@2410',
        database='walletai'
    )
    await conn.execute("ALTER TYPE insighttype ADD VALUE IF NOT EXISTS 'SUCCESS'")
    print("Done: SUCCESS added to insighttype enum.")
    await conn.close()

asyncio.run(main())
