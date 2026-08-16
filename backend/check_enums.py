"""Check what enum types exist in walletai database."""
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        host='localhost', port=5432,
        user='postgres', password='bristi@2410',
        database='walletai'
    )
    rows = await conn.fetch(
        "SELECT typname, enumlabel FROM pg_type t "
        "JOIN pg_enum e ON t.oid = e.enumtypid "
        "ORDER BY typname, enumlabel"
    )
    for r in rows:
        print(f"  {r['typname']}: {r['enumlabel']}")
    await conn.close()

asyncio.run(main())
