#!/usr/bin/env python3
"""Print candidate financial-statement rows from page-delimited PDF text.

This is an inspection aid, not an automatic fact extractor. It deliberately
shows nearby lines and physical PDF page numbers so a human or agent can choose
the consolidated statement row and reject narrative/note-table lookalikes.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

TARGETS = {
    "accounts_receivable": re.compile(r"应收账款"),
    "inventory": re.compile(r"(?:^|\s)存货(?:\s|$)"),
    "revenue": re.compile(r"(?:其中\uff1a|一、)?营业收入"),
    "operating_cost": re.compile(r"(?:其中\uff1a)?营业成本"),
    "net_income": re.compile(r"归属于母公司(?:股东|所有者)的净利润"),
    "operating_cash_flow": re.compile(r"经营活动产生的现金流量净额"),
}


def inspect(path: Path, *, context: int) -> None:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"===== PDF PAGE (\d+) =====", text)
    print(f"\n### {path.stem}")
    for index in range(1, len(parts), 2):
        page = int(parts[index])
        lines = parts[index + 1].splitlines()
        for line_index, line in enumerate(lines):
            matched = [name for name, pattern in TARGETS.items() if pattern.search(line)]
            if not matched:
                continue
            start = max(0, line_index - context)
            end = min(len(lines), line_index + context + 1)
            excerpt = " | ".join(item.strip() for item in lines[start:end] if item.strip())
            print(f"p{page:03d} {','.join(matched)} :: {excerpt}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", type=Path, nargs="+")
    parser.add_argument("--context", type=int, default=1)
    args = parser.parse_args()
    for raw_path in args.paths:
        candidates = sorted(raw_path.glob("*.txt")) if raw_path.is_dir() else [raw_path]
        for candidate in candidates:
            inspect(candidate, context=args.context)


if __name__ == "__main__":
    main()
