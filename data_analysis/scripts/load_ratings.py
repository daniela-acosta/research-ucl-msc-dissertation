"""
load_ratings.py
---------------
Reads JATOS result files from the symmetry rating experiment and outputs a
single combined CSV.

Expected folder layout:
    test_experiment/results/
        study_result_<N>/
            comp-result_<M>/data.txt   ← JSON array of rating rows

Output:
    test_experiment/results/ratings.csv

Usage:
    python data_analysis/scripts/load_ratings.py
    python data_analysis/scripts/load_ratings.py --results-dir path/to/results
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

REPO_ROOT   = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "test_experiment" / "results"
OUTPUT_PATH = RESULTS_DIR / "ratings.csv"


def _study_id(study_dir: Path) -> str:
    m = re.search(r"(\d+)$", study_dir.name)
    return m.group(1) if m else study_dir.name


def load_all(results_dir: Path) -> pd.DataFrame:
    study_dirs = sorted(
        p for p in results_dir.iterdir()
        if p.is_dir() and p.name.startswith("study_result_")
    )
    if not study_dirs:
        raise FileNotFoundError(f"No study_result_* folders found in {results_dir}")

    frames = []
    for study_dir in study_dirs:
        sid = _study_id(study_dir)
        data_files = list(study_dir.glob("comp-result_*/data.txt"))
        if not data_files:
            print(f"  WARNING: no data.txt in {study_dir.name} — skipping")
            continue

        # Each study has one component, so one data file.
        data_file = data_files[0]
        try:
            rows = json.loads(data_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARNING: could not parse {data_file}: {e}")
            continue

        if not isinstance(rows, list) or len(rows) == 0:
            print(f"  WARNING: unexpected format in {data_file} — skipping")
            continue

        df = pd.DataFrame(rows)
        df.insert(0, "study_result_id", sid)
        frames.append(df)
        name = rows[0].get("participant_name", "?")
        print(f"  {study_dir.name}: {len(df)} ratings, participant='{name}'")

    if not frames:
        raise RuntimeError("No usable data found.")

    return pd.concat(frames, ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description="Load symmetry rating results into a CSV.")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--output",      type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    print(f"Results dir : {args.results_dir}")
    print(f"Output      : {args.output}\n")

    df = load_all(args.results_dir)
    df.to_csv(args.output, index=False)

    print(f"\nDone. {len(df)} rows, {df['participant_name'].nunique()} participant(s).")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
