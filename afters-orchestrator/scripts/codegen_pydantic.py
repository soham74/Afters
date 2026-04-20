"""Optional Pydantic codegen from afters-shared/schemas/.

This repo hand-writes Pydantic models in afters/models.py for DX. This script
exists so you can diff against an auto-generated version and catch drift.

Run:  python -m scripts.codegen_pydantic
Output: afters/models/_generated.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "afters-shared" / "schemas"
OUT = Path(__file__).resolve().parents[1] / "afters" / "_models_generated.py"


def main() -> None:
    try:
        import datamodel_code_generator  # noqa: F401
    except ImportError:
        print("datamodel-code-generator not installed. Run: pip install -e .[dev]")
        raise SystemExit(1)

    files = sorted(SCHEMAS.glob("*.schema.json"))
    if not files:
        print(f"no schemas in {SCHEMAS}")
        raise SystemExit(1)

    subprocess.run(
        [
            "datamodel-codegen",
            "--input",
            str(SCHEMAS),
            "--input-file-type",
            "jsonschema",
            "--output",
            str(OUT),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-title-as-name",
            "--use-schema-description",
        ],
        check=True,
    )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
