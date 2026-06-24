#!/usr/bin/env python
"""Manual entrypoint to trigger the feature engineering pipeline.

Usage:
  python scripts/run_features.py
"""

import logging
import sys

from app.config import get_settings
from app.ingestion.storage import default_data_dir
from app.logging_config import configure_logging
from app.modeling.features import build_features

logger = logging.getLogger("uaqf.scripts.run_features")

def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    
    data_dir = default_data_dir()
    
    logger.info("feature_engineering_started")
    try:
        output_path = build_features(data_dir)
        logger.info("feature_engineering_completed", extra={"output_path": str(output_path)})
    except Exception:
        logger.exception("feature_engineering_failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
