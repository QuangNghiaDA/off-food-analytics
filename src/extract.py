"""Download the Open Food Facts Parquet dump to local storage.

Inputs: Hugging Face food.parquet URL; optional ``--force`` to overwrite.
Outputs: file at ``config.PARQUET_PATH`` (``data/raw/food.parquet``).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import requests
from tqdm import tqdm

from config import PARQUET_PATH, RAW_DIR

LOGGER = logging.getLogger(__name__)

SOURCE_URL = (
    "https://huggingface.co/datasets/openfoodfacts/product-database"
    "/resolve/main/food.parquet?download=true"
)
USER_AGENT = "OFFPersonalLearning/1.0 (tqnghia610@gmail.com)"
CHUNK_SIZE = 1024 * 1024
BYTES_PER_GB = 1024 ** 3


def download_parquet(dest: Path, *, force: bool) -> None:
    """Stream the Parquet dump to ``dest``, skipping if it already exists."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force:
        size_gb = dest.stat().st_size / BYTES_PER_GB
        LOGGER.info("File already exists at %s (%.2f GB); skipping. Use --force to re-download.", dest, size_gb)
        return

    part_path = dest.with_suffix(dest.suffix + ".part")
    headers = {"User-Agent": USER_AGENT}

    LOGGER.info("Downloading %s -> %s", SOURCE_URL, dest)
    try:
        with requests.get(
            SOURCE_URL,
            headers=headers,
            stream=True,
            timeout=60,
        ) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0) or 0)

            with part_path.open("wb") as handle, tqdm(
                total=total or None,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=dest.name,
            ) as progress:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    progress.update(len(chunk))
    except Exception:
        if part_path.exists():
            part_path.unlink()
        raise

    part_path.replace(dest)
    size_gb = dest.stat().st_size / BYTES_PER_GB
    LOGGER.info("Download complete: %s (%.2f GB)", dest, size_gb)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Open Food Facts food.parquet.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the destination file already exists.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = parse_args(argv)
    try:
        download_parquet(PARQUET_PATH, force=args.force)
    except Exception:
        LOGGER.exception("Failed to download Parquet file.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
