#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the search engine.
Run after ingest: python scripts/test_search.py "vượt đèn đỏ"
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.search.search_service import search


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "không đội mũ bảo hiểm"
    print(f"Query: {query}\n")
    results = search(query)
    print(f"Top {len(results)} results:\n")
    for i, doc in enumerate(results, 1):
        score = doc.get("score", 0)
        vid = doc.get("violation_id", "")
        desc = (doc.get("description_natural") or "")[:120]
        print(f"  {i}. [{vid}] (score={score:.4f}) {desc}...")
        print(f"     legal_basis: {doc.get('legal_basis', '')[:80]}...")
        print()


if __name__ == "__main__":
    main()
