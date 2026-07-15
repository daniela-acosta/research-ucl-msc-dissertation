"""
load_data.py
------------
Reads raw JATOS result folders and outputs a single combined CSV.

Expected folder layout:
    data/results/
        study_result_<N>/
            comp-result_<M>/data.txt   ← demographics (JSON object, has "age" key)
            comp-result_<K>/data.txt   ← main task    (JSON array)
            comp-result_<J>/data.txt   ← debrief      (JSON object, has "debrief_questions" key)

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
RESULTS_DIR      = REPO_ROOT / "data" / "results"
OUTPUT_PATH      = RESULTS_DIR / "combined_raw.csv"
DEMOGRAPHICS_PATH = RESULTS_DIR / "demographics.csv"

# Matches CONFIG.previewPID in config.js — not a real Prolific ID.
PREVIEW_PID  = "PREVIEW"

# Columns from jsPsych internals that are not useful for analysis.
# trial_index and time_elapsed are kept:
#   trial_index   — sequential position in the jsPsych timeline; used in row_id
#   time_elapsed  — ms since experiment start; session-relative timestamp
JUNK_COLUMNS = [
    "stimulus",
    "internal_node_id",
    "trial_type",
    "correct_position_practice",  # practice artifact that leaks into main-task test rows
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _study_id_from_path(study_dir: Path) -> str:
    """Extract the numeric ID from a study_result_<N> folder name."""
    m = re.search(r"(\d+)$", study_dir.name)
    return m.group(1) if m else study_dir.name


def _load_component(path: Path) -> dict | list | None:
    """Parse a component data.txt file; return None on failure.

    JATOS appends multiple submitResultData calls as newline-separated JSON
    objects in the same file. This function handles that by merging all dict
    objects and returning the first list if any is present.
    """
    try:
        text = path.read_text(encoding="utf-8").strip()
        # Fast path: valid single JSON value.
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Slow path: multiple JSON objects on separate lines.
        objects = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                try:
                    objects.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        if not objects:
            print(f"  WARNING: no parseable JSON in {path}")
            return None
        # Return the trial array if present (main-task component).
        for obj in objects:
            if isinstance(obj, list):
                return obj
        # Otherwise merge all dicts (e.g. debrief_questions + exit_type).
        merged: dict = {}
        for obj in objects:
            if isinstance(obj, dict):
                merged.update(obj)
        return merged or None
    except OSError as e:
        print(f"  WARNING: could not read {path}: {e}")
        return None


def _classify_components(
    study_dir: Path,
) -> tuple[dict | None, list | None, dict | None]:
    """
    Separate the three component types by content:
      - demographics: JSON object with an "age" key
      - main task:    JSON array
      - debrief:      JSON object with a "debrief_questions" key

    Returns (demographics_dict, trials_list, debrief_dict).
    Any element may be None if that component was not found.
    """
    demographics = None
    trials       = None
    debrief      = None

    for comp_dir in sorted(study_dir.iterdir()):
        data_file = comp_dir / "data.txt"
        if not data_file.exists():
            continue
        payload = _load_component(data_file)
        if isinstance(payload, list):
            trials = payload
        elif isinstance(payload, dict):
            if "debrief_questions" in payload:
                debrief = payload
            elif "age" in payload:
                demographics = payload          # demographics component
            # else: consent PID record or exit_type record — skip

    return demographics, trials, debrief


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

def load_all(results_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Walk results_dir, parse every study result, and return:
      - a trial DataFrame (one row per jsPsych trial)
      - a demographics DataFrame (one row per participant)
    """
    all_rows: list[pd.DataFrame] = []
    demo_rows: list[dict] = []

    study_dirs = sorted(
        p for p in results_dir.iterdir()
        if p.is_dir() and p.name.startswith("study_result_")
    )

    if not study_dirs:
        raise FileNotFoundError(f"No study_result_* folders found in {results_dir}")

    for study_dir in study_dirs:
        study_id = _study_id_from_path(study_dir)
        print(f"Loading {study_dir.name} …")

        demographics, trials, debrief = _classify_components(study_dir)

        if trials is None:
            print(f"  WARNING: no main-task data found — skipping.")
            continue

        # Build participant metadata from demographics (or fall back to defaults).
        pid       = ""
        type_map  = {}
        stim_map  = {}
        if demographics:
            pid       = demographics.get("prolific_pid", "")
            type_map  = demographics.get("stimulus_type_map", {})
            stim_map  = demographics.get("stimulus_map", {})

        # Use study_id when prolific_pid is absent or is the preview sentinel,
        # so preview/test runs each get a unique identifier.
        real_pid = pid if (pid and pid != PREVIEW_PID) else ""
        participant_id = real_pid if real_pid else f"local_{study_id}"

        # Collect one demographics row per participant.
        _DEMO_FIELDS = ["age", "gender", "gender_description", "handedness",
                        "vision", "language", "comments"]
        demo_row: dict = {"participant_id": participant_id, "prolific_pid": pid}
        if demographics:
            for field in _DEMO_FIELDS:
                demo_row[field] = demographics.get(field)
            demo_row["stimulus_config"] = demographics.get("stimulus_config")
        demo_rows.append(demo_row)

        df = pd.DataFrame(trials)
        df.insert(0, "participant_id", participant_id)
        df.insert(1, "study_result_id", study_id)
        df.insert(2, "row_id", participant_id + "_" + df["trial_index"].astype(str))

        # Add per-node symmetry type for learning trials (S or A).
        if type_map and "node" in df.columns:
            df["node_symmetry_type"] = df["node"].map(type_map)

        # Add fractal filename columns for test trials.
        if stim_map:
            for col, out in [
                ("node",        "fractal"),
                ("base_node",   "base_fractal"),
                ("option_left",  "option_left_fractal"),
                ("option_right", "option_right_fractal"),
                ("chosen_node",  "chosen_fractal"),
            ]:
                if col in df.columns:
                    df[out] = df[col].map(stim_map)

        # Flatten debrief awareness questions as participant-level columns.
        if debrief:
            dq = debrief.get("debrief_questions", {})
            for key, val in dq.items():
                df[f"debrief_{key}"] = val if val != "" else None

        all_rows.append(df)
        print(f"  {len(df)} trials, participant_id={participant_id}"
              + ("" if debrief else " [no debrief]"))

    if not all_rows:
        raise RuntimeError("No usable data found.")

    combined = pd.concat(all_rows, ignore_index=True)

    # Drop jsPsych internals that are never needed for analysis.
    cols_to_drop = [c for c in JUNK_COLUMNS if c in combined.columns]
    combined.drop(columns=cols_to_drop, inplace=True)

    demographics_df = pd.DataFrame(demo_rows)

    return combined, demographics_df


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
    parser.add_argument(
        "--demographics-out",
        type=Path,
        default=DEMOGRAPHICS_PATH,
        help="Demographics output CSV (default: data/results/demographics.csv)",
    )
    args = parser.parse_args()

    print(f"Results dir      : {args.results_dir}")
    print(f"Trials output    : {args.output}")
    print(f"Demographics out : {args.demographics_out}\n")

    df, demographics_df = load_all(args.results_dir)

    df.to_csv(args.output, index=False)
    demographics_df.to_csv(args.demographics_out, index=False)

    print(f"\nDone. {len(df)} total rows, {df['participant_id'].nunique()} participant(s).")
    print(f"Trial type breakdown:\n{df['trial_type_label'].value_counts(dropna=False).to_string()}")
    print(f"\nSaved trials      → {args.output}")
    print(f"Saved demographics → {args.demographics_out}")


if __name__ == "__main__":
    main()
