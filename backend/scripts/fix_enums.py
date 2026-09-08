"""
scripts/fix_enums.py
─────────────────────
Adds any missing enum values to the walletai PostgreSQL database.
Run this once after adding new enum values that Alembic can't
ALTER TYPE automatically (Alembic requires explicit ADD VALUE statements).

Usage (from backend/ directory):
    python scripts/fix_enums.py

Credentials are read from DATABASE_URL in .env — no hardcoded passwords.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.create_db import _parse_db_url  # reuse the URL parser
from app.core.config import settings

FIXES = [
    "ALTER TYPE insight_type_enum     ADD VALUE IF NOT EXISTS 'SUCCESS'",
    "ALTER TYPE transaction_type_enum ADD VALUE IF NOT EXISTS 'TRANSFER'",
]


async def main() -> None:
    import asyncpg

    parts = _parse_db_url(settings.DATABASE_URL)
    conn = await asyncpg.connect(
        host=parts["host"],
        port=parts["port"],
        user=parts["user"],
        password=parts["password"],
        database=parts["dbname"],
    )
    try:
        for sql in FIXES:
            await conn.execute(sql)
            print(f"OK: {sql.strip()}")
        print("All enum values verified.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
