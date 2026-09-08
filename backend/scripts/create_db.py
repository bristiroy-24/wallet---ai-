"""
scripts/create_db.py
─────────────────────
Run once to create the walletai PostgreSQL database.

Usage (from backend/ directory):
    python scripts/create_db.py

Credentials are read from DATABASE_URL in .env — no hardcoded passwords.
"""

import asyncio
import re
import sys
from pathlib import Path

# Ensure the backend package root is on sys.path when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings


def _parse_db_url(url: str) -> dict:
    """Parse postgresql+asyncpg://user:pass@host:port/dbname into parts."""
    clean = url.replace("postgresql+asyncpg://", "postgresql://")
    m = re.match(
        r"postgresql://(?P<user>[^:]+):(?P<password>[^@]+)@"
        r"(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<dbname>.+)",
        clean,
    )
    if not m:
        raise ValueError(f"Cannot parse DATABASE_URL: {url!r}")
    return {
        "user":     m.group("user"),
        "password": m.group("password"),
        "host":     m.group("host"),
        "port":     int(m.group("port") or 5432),
        "dbname":   m.group("dbname"),
    }


async def main() -> None:
    import asyncpg

    parts = _parse_db_url(settings.DATABASE_URL)
    conn = await asyncpg.connect(
        host=parts["host"],
        port=parts["port"],
        user=parts["user"],
        password=parts["password"],
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", parts["dbname"]
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{parts["dbname"]}"')
            print(f"✅ Database '{parts['dbname']}' created successfully.")
        else:
            print(f"ℹ️  Database '{parts['dbname']}' already exists.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
