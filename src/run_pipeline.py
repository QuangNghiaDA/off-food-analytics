"""Run the whole Open Food Facts pipeline with one command.

Order of steps:
    extract -> load_raw -> staging -> core -> quality -> mart

The quality step sits BEFORE mart on purpose (quality gate): if any
error-level check fails, the pipeline stops and mart is not overwritten.

This script only calls the existing scripts; it does not re-implement them.

Examples:
    python src/run_pipeline.py --dry-run
    python src/run_pipeline.py
    python src/run_pipeline.py --from core
    python src/run_pipeline.py --sample 100000      # WARNING: replaces data with a sample
    python src/run_pipeline.py --force-extract

Exit codes: 0 = all steps OK, 1 = a step failed, 2 = database not reachable.
"""
import argparse
import logging
import subprocess
import sys
import time

import psycopg2

import config

logger = logging.getLogger("run_pipeline")

STEP_NAMES = ["extract", "load_raw", "staging", "core", "quality", "mart"]


def parse_args():
    parser = argparse.ArgumentParser(description="Run the Open Food Facts pipeline.")
    parser.add_argument("--sample", type=int, metavar="N",
                        help="Load only N rows into raw (replaces ALL downstream data with a sample).")
    parser.add_argument("--force-extract", action="store_true",
                        help="Re-download the Parquet file even if it already exists.")
    parser.add_argument("--from", dest="start_from", choices=STEP_NAMES,
                        help="Start from this step and skip the previous ones.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only print the steps and commands; run nothing, no DB connection.")
    return parser.parse_args()


def build_steps(args):
    """Return the ordered list of (step name, command) pairs."""
    py = sys.executable
    extract = [py, "src/extract.py"]
    if args.force_extract:
        extract.append("--force")
    load_raw = [py, "src/load_raw.py"]
    if args.sample:
        load_raw += ["--sample", str(args.sample)]
    return [
        ("extract", extract),
        ("load_raw", load_raw),
        ("staging", [py, "src/run_sql.py", "sql/10_staging.sql"]),
        ("core", [py, "src/run_sql.py", "sql/20_core.sql"]),
        ("quality", [py, "src/run_checks.py"]),
        ("mart", [py, "src/run_sql.py", "sql/30_mart.sql"]),
    ]


def check_db():
    """Try to connect to Postgres (5 s timeout). Never logs the password."""
    try:
        conn = psycopg2.connect(connect_timeout=5, **config.PG)
        conn.close()
        return True
    except Exception as exc:
        logger.error("Cannot connect to PostgreSQL: %s", str(exc).strip())
        logger.error("Check that Docker Desktop is running, then run: docker compose up -d")
        return False


def fmt_time(seconds):
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}m{secs:02d}s"


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()
    steps = build_steps(args)
    start_idx = STEP_NAMES.index(args.start_from) if args.start_from else 0

    if args.sample:
        logger.warning("--sample %d: raw and ALL downstream tables will be replaced "
                       "by a sample. Re-run without --sample to restore full data.", args.sample)

    if args.dry_run:
        for i, (name, cmd) in enumerate(steps):
            status = "SKIPPED" if i < start_idx else "WILL RUN"
            logger.info("%-8s | %-8s | %s", status, name, " ".join(cmd))
        return 0

    if not check_db():
        return 2

    results = []
    failed = False
    total_start = time.perf_counter()

    for i, (name, cmd) in enumerate(steps):
        if i < start_idx or failed:
            results.append((name, "SKIPPED", 0.0))
            continue
        logger.info("=== Step %d/%d: %s ===", i + 1, len(steps), name)
        started = time.perf_counter()
        proc = subprocess.run(cmd, cwd=str(config.ROOT))
        elapsed = time.perf_counter() - started
        if proc.returncode == 0:
            results.append((name, "OK", elapsed))
        else:
            logger.error("Step '%s' failed with exit code %d. Stopping pipeline.",
                         name, proc.returncode)
            results.append((name, "FAILED", elapsed))
            failed = True

    logger.info("---------------- Summary ----------------")
    logger.info("%-10s %-9s %s", "step", "status", "time")
    for name, status, elapsed in results:
        logger.info("%-10s %-9s %s", name, status, fmt_time(elapsed) if elapsed else "-")
    logger.info("Total time: %s", fmt_time(time.perf_counter() - total_start))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())