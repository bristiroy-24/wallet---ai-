"""
scripts/check_enums.py
───────────────────────
Lists all PostgreSQL enum types and their values in the walletai database.
Useful for verifying that migrations applied correctly.

Usage (from backend/ directory):
    python scripts/check_enums.py

Credentials are read from DATABASE_URL in .env — no hardcoded passwords.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.create_db import _parse_db_url
from app.core.config import settings


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
        rows = await conn.fetch(
            "SELECT t.typname, e.enumlabel "
            "FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid "
            "ORDER BY t.typname, e.enumsortorder"
        )
        if not rows:
            print("No enum types found in the database.")
            return
        current = None
        for r in rows:
            if r["typname"] != current:
                current = r["typname"]
                print(f"\n{current}:")
            print(f"  - {r['enumlabel']}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
