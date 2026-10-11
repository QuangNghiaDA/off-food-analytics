"""Run one or more SQL files against PostgreSQL.

Inputs: paths to ``.sql`` files on the command line; connection from ``config.PG``.
Outputs: each file executed in its own transaction; non-zero exit code on failure.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import psycopg2

from config import PG

LOGGER = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute SQL files against PostgreSQL using config.PG."
    )
    parser.add_argument(
        "sql_files",
        nargs="+",
        type=Path,
        metavar="SQL_FILE",
        help="One or more .sql files to run, in order.",
    )
    return parser.parse_args(argv)


def run_sql_file(conn: psycopg2.extensions.connection, path: Path) -> None:
    """Execute one SQL file inside a single transaction and log elapsed time."""
    sql = path.read_text(encoding="utf-8")
    started = time.perf_counter()
    LOGGER.info("Running %s", path)
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    elapsed = time.perf_counter() - started
    LOGGER.info("Finished %s in %.1fs", path, elapsed)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = parse_args(argv)
    try:
        conn = psycopg2.connect(**PG)
        try:
            for path in args.sql_files:
                if not path.is_file():
                    raise FileNotFoundError(f"SQL file not found: {path}")
                run_sql_file(conn, path)
        finally:
            conn.close()
    except Exception:
        LOGGER.exception("Failed to run SQL files.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
