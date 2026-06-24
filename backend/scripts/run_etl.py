#!/usr/bin/env python
"""Manual entrypoint to trigger the ingestion pipeline.

Usage:
  python scripts/run_etl.py --lookback-hours 48
"""

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime, timedelta

from app.config import get_settings
from app.ingestion.etl import run_etl
from app.logging_config import configure_logging

logger = logging.getLogger("uaqf.scripts.run_etl")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the data ingestion pipeline manually.")
    parser.add_argument(
        "--lookback-hours",
        type=int,
        default=get_settings().ingestion_lookback_hours,
        help="How many hours of history to ingest (default: from config)",
    )
    args = parser.parse_args()

    # Need settings to setup logging correctly
    settings = get_settings()
    configure_logging(settings.log_level)

    now = datetime.now(UTC)
    since = now - timedelta(hours=args.lookback_hours)

    logger.info("manual_etl_started", extra={"since": since.isoformat(), "until": now.isoformat()})
    
    try:
        report = run_etl(since, now)
        logger.info(
            "manual_etl_completed",
            extra={
                "duration_s": round(report.duration_s, 2),
                "stations_processed": len(report.stations),
            },
        )
        for station_id, sr in report.stations.items():
            if sr.errors:
                logger.error(f"Station {station_id} had errors: {sr.errors}")
    except Exception as e:
        logger.exception("manual_etl_failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
