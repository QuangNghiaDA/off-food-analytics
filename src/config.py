"""Load project paths and PostgreSQL settings from .env.

Inputs: `.env` at the project root (`POSTGRES_*` variables).
Outputs: `ROOT`, `RAW_DIR`, `PARQUET_PATH`, and `PG`.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

PARQUET_PATH = RAW_DIR / "food.parquet"

PG = {
    "user": os.environ["POSTGRES_USER"],
    "password": os.environ["POSTGRES_PASSWORD"],
    "dbname": os.environ["POSTGRES_DB"],
    "host": os.environ["POSTGRES_HOST"],
    "port": os.environ["POSTGRES_PORT"],
}
