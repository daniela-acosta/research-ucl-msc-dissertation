"""
load_data.py
------------
Reads raw JATOS result folders and outputs a single combined CSV.

Expected folder layout:
    data/results/
        study_result_<N>/
            comp-result_<M>/data.txt   ← demographics (JSON object)
            comp-result_<K>/data.txt   ← main task    (JSON array)

Output:
    data/results/combined_raw.csv

Usage:
    python data_analysis/scripts/load_data.py
    python data_analysis/scripts/load_data.py --results-dir path/to/results
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths (relative to repo root; override with --results-dir)
# ---------------------------------------------------------------------------
REPO_ROOT    = Path(__file__).resolve().parents[2]
RESULTS_DIR  = REPO_ROOT / "data" / "results"
OUTPUT_PATH  = RESULTS_DIR / "combined_raw.csv"

# Columns from jsPsych internals that are not useful for analysis.
# trial_index and time_elapsed are kept:
#   trial_index   — sequential position in the jsPsych timeline; used in row_id
#   time_elapsed  — ms since experiment start; session-relative timestamp
JUNK_COLUMNS = [
    "stimulus",
    "internal_node_id",
    "trial_type",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _study_id_from_path(study_dir: Path) -> str:
    """Extract the numeric ID from a study_result_<N> folder name."""
    m = re.search(r"(\d+)$", study_dir.name)
    return m.group(1) if m else study_dir.name


def _load_component(path: Path) -> dict | list | None:
    """Parse a component data.txt file; return None on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: could not parse {path}: {e}")
        return None


def _classify_components(study_dir: Path) -> tuple[dict | None, list | None]:
    """
    Separate demographics (JSON object) from main-task (JSON array) files.
    Returns (demographics_dict, trials_list). Either may be None if not found.
    """
    demographics = None
    trials       = None

    for comp_dir in sorted(study_dir.iterdir()):
        data_file = comp_dir / "data.txt"
        if not data_file.exists():
            continue
        payload = _load_component(data_file)
        if isinstance(payload, dict):
            demographics = payload
        elif isinstance(payload, list):
            trials = payload

    return demographics, trials


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

def load_all(results_dir: Path) -> pd.DataFrame:
    """
    Walk results_dir, parse every study result, and return a single DataFrame
    with one row per jsPsych trial, tagged with participant metadata.
    """
    all_rows: list[pd.DataFrame] = []

    study_dirs = sorted(
        p for p in results_dir.iterdir()
        if p.is_dir() and p.name.startswith("study_result_")
    )

    if not study_dirs:
        raise FileNotFoundError(f"No study_result_* folders found in {results_dir}")

    for study_dir in study_dirs:
        study_id = _study_id_from_path(study_dir)
        print(f"Loading {study_dir.name} …")

        demographics, trials = _classify_components(study_dir)

        if trials is None:
            print(f"  WARNING: no main-task data found — skipping.")
            continue

        # Build participant metadata from demographics (or fall back to defaults).
        pid = ""
        if demographics:
            pid = demographics.get("prolific_pid", "")

        # Use study_id as participant identifier when prolific_pid is absent
        # (e.g. local test runs).
        participant_id = pid if pid else f"local_{study_id}"

        df = pd.DataFrame(trials)
        df.insert(0, "participant_id", participant_id)
        df.insert(1, "study_result_id", study_id)
        df.insert(2, "row_id", participant_id + "_" + df["trial_index"].astype(str))

        all_rows.append(df)
        print(f"  {len(df)} trials, participant_id={participant_id}")

    if not all_rows:
        raise RuntimeError("No usable data found.")

    combined = pd.concat(all_rows, ignore_index=True)

    # Drop jsPsych internals that are never needed for analysis.
    cols_to_drop = [c for c in JUNK_COLUMNS if c in combined.columns]
    combined.drop(columns=cols_to_drop, inplace=True)

    return combined


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Load JATOS results into a combined CSV.")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS_DIR,
        help="Path to the results directory (default: data/results/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Output CSV path (default: data/results/combined_raw.csv)",
    )
    args = parser.parse_args()

    print(f"Results dir : {args.results_dir}")
    print(f"Output      : {args.output}\n")

    df = load_all(args.results_dir)

    df.to_csv(args.output, index=False)

    print(f"\nDone. {len(df)} total rows, {df['participant_id'].nunique()} participant(s).")
    print(f"Trial type breakdown:\n{df['trial_type_label'].value_counts(dropna=False).to_string()}")
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
