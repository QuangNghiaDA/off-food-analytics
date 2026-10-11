"""Run read-only data quality checks against PostgreSQL core tables.

Inputs: ``sql/90_quality_checks.sql`` and connection settings from ``config.PG``.
Outputs: a logged results table (check name, severity, violation count, status),
totals for FAIL and WARN, and process exit code 1 if any check FAILs.
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg2

from config import PG, ROOT

LOGGER = logging.getLogger(__name__)

CHECKS_PATH = ROOT / "sql" / "90_quality_checks.sql"
HEADER_RE = re.compile(
    r"^-- check:\s*(?P<name>\S+)\s*\|\s*severity:\s*(?P<severity>\S+)\s*$"
)


@dataclass(frozen=True)
class Check:
    name: str
    severity: str
    sql: str


def parse_checks(sql_text: str) -> list[Check]:
    """Split SQL text into checks keyed by ``-- check:`` header lines."""
    checks: list[Check] = []
    lines = sql_text.splitlines()
    i = 0
    while i < len(lines):
        match = HEADER_RE.match(lines[i].strip())
        if match is None:
            i += 1
            continue

        name = match.group("name")
        severity = match.group("severity").lower()
        sql_parts: list[str] = []
        i += 1
        while i < len(lines):
            sql_parts.append(lines[i])
            if ";" in lines[i]:
                break
            i += 1

        sql = "\n".join(sql_parts).strip()
        if not sql:
            raise ValueError(f"Check '{name}' has no SQL statement.")
        checks.append(Check(name=name, severity=severity, sql=sql))
        i += 1
    return checks


def status_for(severity: str, violations: int) -> str:
    if violations == 0:
        return "PASS"
    if severity == "warn":
        return "WARN"
    return "FAIL"


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        sql_text = CHECKS_PATH.read_text(encoding="utf-8")
        checks = parse_checks(sql_text)
    except Exception:
        LOGGER.exception("Failed to read or parse %s.", CHECKS_PATH)
        return 1

    if not checks:
        LOGGER.error("No checks found in %s.", CHECKS_PATH)
        return 1

    LOGGER.info("Running %s quality checks from %s.", len(checks), CHECKS_PATH)

    try:
        conn = psycopg2.connect(**PG)
    except Exception:
        LOGGER.exception("Failed to connect to PostgreSQL.")
        return 1

    fail_count = 0
    warn_count = 0
    rows: list[tuple[str, str, int, str]] = []

    try:
        for check in checks:
            try:
                with conn.cursor() as cur:
                    cur.execute(check.sql)
                    fetched = cur.fetchone()
                    violations = int(fetched[0]) if fetched is not None else 0
            except Exception:
                LOGGER.exception("SQL error in check '%s'.", check.name)
                return 1

            status = status_for(check.severity, violations)
            if status == "FAIL":
                fail_count += 1
            elif status == "WARN":
                warn_count += 1
            rows.append((check.name, check.severity, violations, status))
    finally:
        conn.close()

    header = f"{'check':<28} {'severity':<10} {'violations':>12}  {'status'}"
    LOGGER.info("%s", header)
    LOGGER.info("%s", "-" * len(header))
    for name, severity, violations, status in rows:
        LOGGER.info("%-28s %-10s %12d  %s", name, severity, violations, status)

    LOGGER.info("FAIL: %s", fail_count)
    LOGGER.info("WARN: %s", warn_count)
    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
