"""Fix missing enum values in walletai PostgreSQL database."""
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        host='localhost', port=5432,
        user='postgres', password='bristi@2410',
        database='walletai'
    )
    fixes = [
        "ALTER TYPE insight_type_enum ADD VALUE IF NOT EXISTS 'SUCCESS'",
        "ALTER TYPE transaction_type_enum ADD VALUE IF NOT EXISTS 'TRANSFER'",
    ]
    for sql in fixes:
        await conn.execute(sql)
        print(f"OK: {sql}")
    await conn.close()
    print("All enum values fixed.")

asyncio.run(main())
