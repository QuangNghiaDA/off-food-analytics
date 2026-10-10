"""Load Open Food Facts Parquet into PostgreSQL ``raw.off_products`` via DuckDB.

Inputs: ``config.PARQUET_PATH``, ``config.PG``; optional ``--sample N`` to load
the first N rows only.
Outputs: PostgreSQL table ``raw.off_products`` (full refresh), plus a logged
row count.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

import duckdb

from config import PARQUET_PATH, PG

LOGGER = logging.getLogger(__name__)

SOURCE_COLUMNS = (
    "code",
    "product_name",
    "brands",
    "brands_tags",
    "categories_tags",
    "food_groups_tags",
    "countries_tags",
    "nutriscore_grade",
    "nutriscore_score",
    "nova_group",
    "environmental_score_grade",
    "environmental_score_score",
    "nutriments",
    "nutrient_levels_tags",
    "nutrition_data_per",
    "no_nutrition_data",
    "ingredients_n",
    "additives_n",
    "additives_tags",
    "allergens_tags",
    "ingredients_analysis_tags",
    "ingredients_from_palm_oil_n",
    "labels_tags",
    "quantity",
    "product_quantity",
    "product_quantity_unit",
    "completeness",
    "data_quality_errors_tags",
    "created_t",
    "last_modified_t",
    "lang",
    "data_sources_tags",
)

JSON_COLUMNS = frozenset(
    {
        "product_name",
        "nutriments",
        "brands_tags",
        "categories_tags",
        "food_groups_tags",
        "countries_tags",
        "nutrient_levels_tags",
        "additives_tags",
        "allergens_tags",
        "ingredients_analysis_tags",
        "labels_tags",
        "data_quality_errors_tags",
        "data_sources_tags",
    }
)

PG_ALIAS = "pg"
TARGET_TABLE = f"{PG_ALIAS}.raw.off_products"


def _sql_string(value: str) -> str:
    """Escape a Python string for use as a SQL string literal."""
    return "'" + value.replace("'", "''") + "'"


def _postgres_attach_string() -> str:
    """Build a DuckDB ATTACH connection string from ``config.PG``."""
    return (
        f"dbname={PG['dbname']} "
        f"user={PG['user']} "
        f"password={PG['password']} "
        f"host={PG['host']} "
        f"port={PG['port']}"
    )


def _select_list() -> str:
    """Return the SELECT list: 32 source columns plus ingest metadata."""
    parts: list[str] = []
    for name in SOURCE_COLUMNS:
        if name in JSON_COLUMNS:
            parts.append(f"to_json({name})::VARCHAR AS {name}_json")
        else:
            parts.append(name)
    parts.append("now() AS _ingested_at")
    parts.append(f"{_sql_string(PARQUET_PATH.name)} AS _source_file")
    return ",\n        ".join(parts)


def _load_sql(*, sample: int | None) -> str:
    parquet = _sql_string(PARQUET_PATH.resolve().as_posix())
    limit_clause = f"\nLIMIT {sample}" if sample is not None else ""
    return f"""
DROP TABLE IF EXISTS {TARGET_TABLE};
CREATE TABLE {TARGET_TABLE} AS
SELECT
        {_select_list()}
FROM read_parquet({parquet}){limit_clause};
"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load food.parquet into PostgreSQL raw.off_products."
    )
    parser.add_argument(
        "--sample",
        type=int,
        metavar="N",
        default=None,
        help="Load only the first N rows instead of the full file.",
    )
    return parser.parse_args(argv)


def load_raw(*, sample: int | None) -> int:
    """Full-refresh ``raw.off_products`` from Parquet; return the loaded row count."""
    if sample is not None and sample < 1:
        raise ValueError("--sample must be a positive integer")
    if not PARQUET_PATH.is_file():
        raise FileNotFoundError(f"Parquet file not found: {PARQUET_PATH}")

    started = time.perf_counter()
    LOGGER.info(
        "Loading %s into %s%s",
        PARQUET_PATH,
        TARGET_TABLE,
        f" (sample={sample})" if sample is not None else " (full file)",
    )

    con = duckdb.connect()
    try:
        con.execute("INSTALL postgres;")
        con.execute("LOAD postgres;")
        # Postgres không cho phép NUL byte trong VARCHAR, nên bỏ các ký tự này khi nạp.
        con.execute("SET pg_null_byte_replacement = '';")
        con.execute(
            f"ATTACH {_sql_string(_postgres_attach_string())} AS {PG_ALIAS} (TYPE postgres);"
        )
        con.execute(_load_sql(sample=sample))
        row_count = con.execute(f"SELECT count(*) FROM {TARGET_TABLE}").fetchone()[0]
    finally:
        con.close()

    elapsed = time.perf_counter() - started
    LOGGER.info(
        "Loaded %s rows into raw.off_products in %.1fs from %s",
        row_count,
        elapsed,
        PARQUET_PATH.name,
    )
    return int(row_count)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = parse_args(argv)
    try:
        load_raw(sample=args.sample)
    except Exception:
        LOGGER.exception("Failed to load Parquet into raw.off_products.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
