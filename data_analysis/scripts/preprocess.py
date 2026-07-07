"""
preprocess.py
-------------
Loads combined_raw.csv, cleans types, derives analysis variables, and outputs:

    data/results/test_trials.csv      ← 2AFC test trials  (main analysis)
    data/results/learning_trials.csv  ← cover-task trials (supplementary)

Derived variables added to test_trials:
    accuracy      1/0 for T1 trials (chose plausible option); NaN for T0/T2 and timeouts
    confidence_z  confidence_response z-scored within each participant

Usage:
    python data_analysis/scripts/preprocess.py
    python data_analysis/scripts/preprocess.py --input path/to/combined_raw.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT    = Path(__file__).resolve().parents[2]
RESULTS_DIR  = REPO_ROOT / "data" / "results"
INPUT_PATH   = RESULTS_DIR / "combined_raw.csv"
TEST_OUT     = RESULTS_DIR / "test_trials.csv"
LEARNING_OUT = RESULTS_DIR / "learning_trials.csv"

# Cover task response keys — must match CONFIG.coverTask in config.js.
COVER_KEY_SYMMETRIC     = "f"
COVER_KEY_NOT_SYMMETRIC = "j"

# ---------------------------------------------------------------------------
# Column type definitions
# ---------------------------------------------------------------------------

# Columns that should be boolean. Come through as object dtype from JSON→CSV round-trip.
BOOL_COLS = [
    "left_is_option_a",
    "option_a_plausible",
    "option_b_plausible",
    "chose_option_a",
    "chose_plausible",
    "timed_out",
    "confidence_timed_out",
]

# Columns that should be integer (block, category, etc.).
INT_COLS = [
    "block",
    "category",
    "trial_index",
    "trial_index_in_block",
    "question_number",
    "step",
    "stimulus_config",
]

# Explicit column selection for each output — prevents columns from other trial
# types leaking in (e.g. cover_response appearing in test_trials).
TEST_COLS = [
    # identifiers
    "participant_id", "study_result_id", "row_id",
    # session position
    "trial_index", "time_elapsed", "block", "trial_index_in_block",
    # question metadata
    "question_code", "question_number", "category",
    "comparison_pair_tag", "comparison_type",
    # stimulus
    "base_node", "base_fractal",
    "option_left", "option_left_fractal",
    "option_right", "option_right_fractal",
    "left_is_option_a", "option_a_plausible", "option_b_plausible",
    # response
    "rt", "response", "chosen_position", "chosen_node", "chosen_fractal",
    "chose_option_a", "chose_plausible", "timed_out",
    # confidence
    "confidence_response", "confidence_rt", "confidence_timed_out",
    # participant config
    "stimulus_config",
    # derived
    "accuracy", "confidence_z",
]

LEARNING_COLS = [
    # identifiers
    "participant_id", "study_result_id", "row_id",
    # session position
    "trial_index", "time_elapsed", "block", "step",
    # stimulus
    "node", "fractal", "node_symmetry_type",
    # response
    "cover_response", "cover_rt",
    # participant config
    "stimulus_config",
    # derived
    "responded", "cover_correct",
]


# ---------------------------------------------------------------------------
# Type-fixing helpers
# ---------------------------------------------------------------------------

def _fix_bool(series: pd.Series) -> pd.Series:
    """Convert object-typed True/False (or 'True'/'False' strings) to pandas BooleanDtype.
    Preserves NaN as pd.NA."""
    return series.map(
        lambda v: True if v is True or v == "True"
        else (False if v is False or v == "False"
        else pd.NA)
    ).astype(pd.BooleanDtype())


def _fix_int(series: pd.Series) -> pd.Series:
    """Convert float64 columns to nullable Int64 (preserves NaN as pd.NA)."""
    return series.astype(pd.Int64Dtype())


def fix_types(df: pd.DataFrame) -> pd.DataFrame:
    for col in BOOL_COLS:
        if col in df.columns:
            df[col] = _fix_bool(df[col])
    for col in INT_COLS:
        if col in df.columns:
            df[col] = _fix_int(df[col])
    return df


# ---------------------------------------------------------------------------
# Derived variables
# ---------------------------------------------------------------------------

def add_accuracy(df: pd.DataFrame) -> pd.DataFrame:
    """
    accuracy: 1 if the participant chose the plausible option, 0 if not.
    Defined only for T1 trials (one plausible, one implausible option).
    NaN for T0/T2 (no clear correct answer) and for timed-out trials.
    """
    is_t1        = df["comparison_type"] == "T1"
    not_timedout = ~df["timed_out"].fillna(True)
    df["accuracy"] = np.where(
        is_t1 & not_timedout,
        df["chose_plausible"].astype(float),
        np.nan
    )
    return df


def add_confidence_z(df: pd.DataFrame) -> pd.DataFrame:
    """
    confidence_z: confidence_response z-scored within each participant.
    NaN for timed-out confidence trials (confidence_response is null).
    """
    df["confidence_z"] = df.groupby("participant_id")["confidence_response"].transform(
        lambda x: (x - x.mean()) / x.std(ddof=1)
    )
    return df


def add_cover_correct(df: pd.DataFrame) -> pd.DataFrame:
    """
    cover_correct: True if the participant correctly judged the stimulus symmetry.
    Derived from node_symmetry_type (S/A, from demographics stimulus_type_map)
    and the configured cover task response keys.
    NaN if no response was given (timed out / missed).
    """
    correct_key = df["node_symmetry_type"].map({
        "S": COVER_KEY_SYMMETRIC,
        "A": COVER_KEY_NOT_SYMMETRIC,
    })
    has_response = df["cover_response"].notna()
    df["cover_correct"] = np.where(
        has_response,
        df["cover_response"] == correct_key,
        np.nan
    )
    return df


# ---------------------------------------------------------------------------
# Main preprocessing
# ---------------------------------------------------------------------------

def preprocess(input_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(input_path)
    print(f"Loaded {len(raw)} rows from {input_path}")

    raw = fix_types(raw)

    # ── Test trials ─────────────────────────────────────────────────────────
    test = raw[raw["trial_type_label"] == "test"].copy()
    test = add_accuracy(test)
    test = add_confidence_z(test)
    test = test[[c for c in TEST_COLS if c in test.columns]].copy()
    test.reset_index(drop=True, inplace=True)

    print(f"\nTest trials : {len(test)} rows, {test['participant_id'].nunique()} participant(s)")
    print(f"  accuracy defined (T1, responded): {test['accuracy'].notna().sum()} / {len(test)}")
    _summarise_test(test)

    # ── Learning trials ──────────────────────────────────────────────────────
    learning = raw[raw["trial_type_label"] == "learning"].copy()
    learning["responded"] = learning["cover_response"].notna()
    learning = add_cover_correct(learning)
    learning = learning[[c for c in LEARNING_COLS if c in learning.columns]].copy()
    learning.reset_index(drop=True, inplace=True)

    print(f"\nLearning trials : {len(learning)} rows")
    print(f"  response rate  : {learning['responded'].mean():.1%}")
    print(f"  cover accuracy : {learning['cover_correct'].dropna().mean():.1%} "
          f"(of {learning['cover_correct'].notna().sum()} responded trials)")

    return test, learning


def _summarise_test(df: pd.DataFrame) -> None:
    print(f"  comparison_type counts:\n"
          + df["comparison_type"].value_counts().to_string().replace("^", "    "))
    if df["accuracy"].notna().any():
        print(f"  mean accuracy (T1): {df['accuracy'].mean():.3f}")
    print(f"  timeout rate: {df['timed_out'].mean():.1%}")
    print(f"  confidence timeout rate: {df['confidence_timed_out'].mean():.1%}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Preprocess combined_raw.csv for analysis.")
    parser.add_argument("--input",   type=Path, default=INPUT_PATH)
    parser.add_argument("--test-out",     type=Path, default=TEST_OUT)
    parser.add_argument("--learning-out", type=Path, default=LEARNING_OUT)
    args = parser.parse_args()

    test, learning = preprocess(args.input)

    test.to_csv(args.test_out, index=False)
    learning.to_csv(args.learning_out, index=False)

    print(f"\nSaved test_trials     → {args.test_out}")
    print(f"Saved learning_trials → {args.learning_out}")


if __name__ == "__main__":
    main()
