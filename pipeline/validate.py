"""Validate artefact Parquet files against schema v1.  Usage: python pipeline/validate.py <dir>"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schemas import SCHEMAS, validate


def main(d: str) -> int:
    problems = []
    for name in SCHEMAS:
        p = Path(d) / f"{name}.parquet"
        if not p.exists():
            print(f"skip {name} (not present)")
            continue
        df = pd.read_parquet(p)
        errs = validate(name, df)
        print(
            f"{name}: {len(df)} rows, {'OK' if not errs else f'{len(errs)} problems'}"
        )
        problems += errs
    for e in problems:
        print("  -", e)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "artefacts/v1"))
