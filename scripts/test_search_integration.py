#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test: requires OpenSearch up and data ingested.
  python scripts/ingest_violations.py   # first
  python scripts/test_search_integration.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.search.search_service import search


def main() -> int:
    queries = [
        "vượt đèn đỏ",
        "không đội mũ bảo hiểm",
        "dừng xe đột ngột",
    ]
    for q in queries:
        print(f"Query: {q}")
        try:
            results = search(q)
            print(f"  -> {len(results)} results")
            for r in results[:2]:
                print(f"     - {r.get('violation_id')} (score={r.get('score', 0):.4f})")
        except Exception as e:
            print(f"  -> Error: {e}")
            return 1
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
