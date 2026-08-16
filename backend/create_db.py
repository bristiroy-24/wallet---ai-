"""
create_db.py – Run once to create the walletai database.
Usage: python create_db.py
"""
import asyncio
import asyncpg

async def main():
    # Connect to the default 'postgres' database to create 'walletai'
    conn = await asyncpg.connect(
        host='localhost', port=5432,
        user='postgres', password='bristi@2410',
        database='postgres'
    )
    # Check if already exists
    exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname='walletai'"
    )
    if not exists:
        await conn.execute('CREATE DATABASE walletai')
        print("✅ Database 'walletai' created successfully.")
    else:
        print("ℹ️  Database 'walletai' already exists.")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
