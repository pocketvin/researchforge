"""Export V2 JSON schemas from the canonical Pydantic contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from researchforge.v2.schema_exports import V2_SCHEMA_MODELS, export_schema


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("schemas/v2"))
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, model in V2_SCHEMA_MODELS.items():
        path = output_dir / filename
        payload = export_schema(model, filename)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), "schemas": len(V2_SCHEMA_MODELS)}))


if __name__ == "__main__":
    main()
