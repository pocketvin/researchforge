#!/usr/bin/env python3
"""Extract page-delimited text from ignored primary Benchmark PDFs."""

from __future__ import annotations

import argparse
from pathlib import Path

from pypdf import PdfReader


def extract_directory(raw_dir: Path) -> list[tuple[str, int, int]]:
    """Write one ignored UTF-8 text file beside each PDF."""
    results: list[tuple[str, int, int]] = []
    for pdf_path in sorted(raw_dir.glob("*.pdf")):
        reader = PdfReader(pdf_path)
        chunks = [
            f"\n\n===== PDF PAGE {number} =====\n\n{page.extract_text() or ''}"
            for number, page in enumerate(reader.pages, start=1)
        ]
        content = "".join(chunks)
        pdf_path.with_suffix(".txt").write_text(content, encoding="utf-8")
        results.append((pdf_path.name, len(reader.pages), len(content)))
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/v1.4-primary"),
    )
    args = parser.parse_args()
    for filename, page_count, character_count in extract_directory(args.raw_dir):
        print(f"{filename}: pages={page_count}; characters={character_count}")


if __name__ == "__main__":
    main()
