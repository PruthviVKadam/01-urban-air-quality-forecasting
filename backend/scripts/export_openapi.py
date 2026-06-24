"""Dump the live OpenAPI schema to backend/openapi.json (the typed contract).

The frontend generates its TypeScript types from this file, so it is committed and
regenerated whenever the schema changes (CI verifies it is in sync).
"""

import json
from pathlib import Path

from app.main import app

OUTPUT = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUTPUT.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(schema['paths'])} paths)")


if __name__ == "__main__":
    main()
