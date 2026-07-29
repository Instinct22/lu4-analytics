#!/usr/bin/env python3
"""Finalize items_encyclopedia.json as a self-contained library (no lu4/l2map paths)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from encyclopedia_lib import finalize_payload  # noqa: E402

DEFAULT_IN = ROOT / "data" / "datasets" / "items_encyclopedia.json"
DEFAULT_OUT = DEFAULT_IN
CRAFT_CATALOG = ROOT / "data" / "datasets" / "craft_catalog.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize self-contained items encyclopedia")
    parser.add_argument("--in", dest="inp", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--no-craft-merge", action="store_true", help="Skip merging craft_catalog meta")
    args = parser.parse_args()

    if not args.inp.is_file():
        raise SystemExit(f"Input not found: {args.inp}")

    payload = json.loads(args.inp.read_text(encoding="utf-8"))
    craft = None
    if not args.no_craft_merge and CRAFT_CATALOG.is_file():
        craft = json.loads(CRAFT_CATALOG.read_text(encoding="utf-8"))

    finalized = finalize_payload(payload, craft_catalog=craft)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(finalized, f, ensure_ascii=False, indent=2)

    print(f"Finalized {finalized['item_count']} items -> {args.out}")
    print("Library:", finalized.get("library"))
    print("Sections:", finalized.get("section_counts"))


if __name__ == "__main__":
    main()
