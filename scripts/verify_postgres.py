"""Run migration and persistence tests in a disposable local PostgreSQL database.

From backend/: PYTHONPATH=. uv run python ../scripts/verify_postgres.py
Uses the configured local PostgreSQL credentials, never ServiceNow or Gemini APIs.
"""

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import uuid

import asyncpg
from sqlalchemy.engine import make_url
from app.core.config import get_settings


async def run() -> int:
    url = make_url(get_settings().database_url)
    if url.host not in {"localhost", "127.0.0.1", "db"}:
        raise RuntimeError(
            "Disposable database verification requires a local PostgreSQL host"
        )
    admin = await asyncpg.connect(
        host=url.host,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        database=url.database,
        timeout=10,
    )
    name = "service_desk_test_" + uuid.uuid4().hex[:12]
    test_url = url.set(database=name).render_as_string(hide_password=False)
    env = {
        **os.environ,
        "DATABASE_URL": test_url,
        "TEST_POSTGRES_URL": test_url,
        "GEMINI_API_KEY": "",
        "USE_MOCK_SERVICENOW": "true",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    backend = Path(__file__).resolve().parents[1] / "backend"
    created = False
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        created = True
        steps = [
            ["alembic", "upgrade", "head"],
            [
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_postgres_integration.py",
            ],
            ["alembic", "downgrade", "base"],
            ["alembic", "upgrade", "head"],
        ]
        for step in steps:
            print("Running:", " ".join(step), flush=True)
            result = await asyncio.to_thread(
                subprocess.run, [sys.executable, "-m", *step], cwd=backend, env=env
            )
            if result.returncode:
                return result.returncode
        print(
            "Disposable PostgreSQL verification and migration round-trip passed.",
            flush=True,
        )
        return 0
    finally:
        if created:
            await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
            print("Disposable test database removed.", flush=True)
        await admin.close()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run()))
    except Exception as exc:
        print(
            f"PostgreSQL verification incomplete ({type(exc).__name__}); no credentials printed."
        )
        raise SystemExit(1) from None
