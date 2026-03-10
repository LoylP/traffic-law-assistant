#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ingest violations_300.json into OpenSearch + document store.
Uses src.search.ingest.ingest_violations_file (reusable load path).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.search.document_store import get_db_path
from src.search.ingest import ingest_violations_file

VIOLATIONS_PATH = ROOT / "data" / "structured" / "violations_300.json"


def main() -> None:
    if not VIOLATIONS_PATH.exists():
        print(f"File not found: {VIOLATIONS_PATH}")
        sys.exit(1)
    print(f"Ingesting from {VIOLATIONS_PATH} ...")
    count = ingest_violations_file(VIOLATIONS_PATH)
    print(f"Done. Indexed {count} documents. DB: {get_db_path()}")


if __name__ == "__main__":
    main()
