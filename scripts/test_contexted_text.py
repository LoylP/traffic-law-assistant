#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test _contexted_text(): generate search-optimized contexted text for violation docs.
Run from repo root: python scripts/test_contexted_text.py [path_to_violations.json]
If no path given, uses a few inline samples.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.search.ingest import _contexted_text

# Inline samples if no file provided
SAMPLE_DOCS = [
    {
        "description_natural": "Không chấp hành tín hiệu đèn giao thông: Vượt đèn đỏ, đèn vàng",
        "vehicle_type": "xe máy",
        "context_condition": "đèn tín hiệu",
    },
    {
        "description_natural": "Dừng xe đột ngột; chuyển hướng không báo hiệu trước",
        "vehicle_type": "xe đạp",
        "context_condition": "dừng/đỗ",
    },
    {
        "description_natural": "Vượt bên phải trong các trường hợp không được phép",
        "vehicle_type": "xe đạp",
        "context_condition": "",
    },
]


def main() -> None:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        docs = data if isinstance(data, list) else [data]
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        docs = docs[:limit]
        print(f"Testing {len(docs)} doc(s) from {path}\n")
    else:
        docs = SAMPLE_DOCS
        print("Testing inline samples\n")

    for i, doc in enumerate(docs, 1):
        desc = (doc.get("description_natural") or "").strip()
        if len(desc) > 80:
            desc = desc[:80] + "..."
        print(f"--- Doc {i} ---")
        print("  description_natural:", desc or "(empty)")
        print("  vehicle_type:", doc.get("vehicle_type") or "")
        print("  context_condition:", doc.get("context_condition") or "")
        result = _contexted_text(doc)
        print("  contexted_text:", result)
        print()
    print("Done.")


if __name__ == "__main__":
    main()
