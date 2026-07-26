"""
preprocess.py
-------------
Loads combined_raw.csv, cleans types, derives analysis variables, and outputs:

    data/results/test_trials.csv      ← 2AFC test trials  (main analysis)
    data/results/learning_trials.csv  ← cover-task trials (supplementary)

Derived variables added to test_trials:
    correct                 1/0 for T1 trials (chose plausible option); 0 for T1 timeouts; NaN for T0/T2
    confidence_z            confidence_response z-scored within each participant
    correct_dest_community       W or X — plausible option's community relation to base node; NaN for T0/T2
    correct_dest_node_type       B or NB — plausible option's node type; NaN for T0/T2
    is_dest_community_comparison True if the pair contrasts W vs X destination community
    is_dest_node_type_comparison True if the pair contrasts B vs NB destination node type
    chosen_community_is_X        1/0 — did participant choose X option; NaN if not a community comparison or timed out
    chosen_nodetype_is_B         1/0 — did participant choose B destination; NaN if not a node-type comparison or timed out

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
    "confidence_slider_start",
    # participant config
    "stimulus_config",
    # derived
    "correct", "confidence_z",
    "correct_dest_community", "correct_dest_node_type",
    "is_dest_community_comparison", "is_dest_node_type_comparison",
    "chosen_community_is_X", "chosen_nodetype_is_B",
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

def add_correct(df: pd.DataFrame) -> pd.DataFrame:
    """
    correct: 1 if the participant chose the plausible option, 0 if not.
    Defined only for T1 trials (one plausible, one implausible option).
    NaN for T0/T2 (no clear correct answer) and for timed-out trials.
    """
    is_t1        = df["comparison_type"] == "T1"
    not_timedout = ~df["timed_out"].fillna(True)
    df["correct"] = np.where(
        is_t1 & not_timedout,
        df["chose_plausible"].astype(float),
        np.where(is_t1, 0.0, np.nan)  # T1 timeouts → 0; T0/T2 → NaN (no correct answer)
    )
    return df


def add_correct_option_properties(df: pd.DataFrame) -> pd.DataFrame:
    """
    correct_dest_community: W (within) or X (cross-community) for the plausible option.
    correct_dest_node_type: B (boundary) or NB (non-boundary) for the plausible option.
    Both are NaN for T0 (no plausible option) and T2 (both options plausible).
    Derived by parsing the comparison_pair_tag, e.g. 'NB1WB__NB2XB'.
    """
    tags = df["comparison_pair_tag"].str.split("__", expand=True)
    tag_a, tag_b = tags[0], tags[1]

    # Regex: (base_type)(steps)(W|X)(NB|B) — try NB before B in dest group
    _wc  = r"^(?:NB|B)\d(W|X)(?:NB|B)$"   # captures within-code
    _dt  = r"^(?:NB|B)\d(?:W|X)(NB|B)$"   # captures dest node type

    wc_a = tag_a.str.extract(_wc, expand=False)
    dt_a = tag_a.str.extract(_dt, expand=False)
    wc_b = tag_b.str.extract(_wc, expand=False)
    dt_b = tag_b.str.extract(_dt, expand=False)

    is_a = df["option_a_plausible"].fillna(False).astype(bool)
    is_b = df["option_b_plausible"].fillna(False).astype(bool)
    is_t1 = is_a ^ is_b  # exactly one plausible → T1

    df["correct_dest_community"] = pd.NA
    df["correct_dest_node_type"] = pd.NA
    df.loc[is_t1 & is_a, "correct_dest_community"] = wc_a[is_t1 & is_a]
    df.loc[is_t1 & is_a, "correct_dest_node_type"] = dt_a[is_t1 & is_a]
    df.loc[is_t1 & is_b, "correct_dest_community"] = wc_b[is_t1 & is_b]
    df.loc[is_t1 & is_b, "correct_dest_node_type"] = dt_b[is_t1 & is_b]
    return df


def add_choice_bias_variables(df: pd.DataFrame) -> pd.DataFrame:
    """
    Variables for choice-bias analysis, independent of which option is plausible.

    is_dest_community_comparison: True when one option is a W transition and the
        other is X (the pair contrasts community membership of the destination).
    is_dest_node_type_comparison: True when one option has a B destination and the
        other has NB (the pair contrasts boundary vs non-boundary destination).

    chosen_community_is_X: 1 if the participant chose the X option, 0 if W.
        NaN when is_dest_community_comparison is False or the trial timed out.
    chosen_nodetype_is_B: 1 if the participant chose the B destination, 0 if NB.
        NaN when is_dest_node_type_comparison is False or the trial timed out.
    """
    tags = df["comparison_pair_tag"].str.split("__", expand=True)
    tag_a, tag_b = tags[0], tags[1]

    _wc = r"^(?:NB|B)\d(W|X)(?:NB|B)$"
    _dt = r"^(?:NB|B)\d(?:W|X)(NB|B)$"

    wc_a = tag_a.str.extract(_wc, expand=False)
    dt_a = tag_a.str.extract(_dt, expand=False)
    wc_b = tag_b.str.extract(_wc, expand=False)
    dt_b = tag_b.str.extract(_dt, expand=False)

    df["is_dest_community_comparison"] = wc_a != wc_b
    df["is_dest_node_type_comparison"]  = dt_a != dt_b

    chose_a      = df["chose_option_a"].fillna(False).astype(bool)
    not_timed_out = ~df["timed_out"].fillna(True).astype(bool)

    chosen_wc = np.where(chose_a, wc_a, wc_b)
    chosen_dt = np.where(chose_a, dt_a, dt_b)

    is_comm = df["is_dest_community_comparison"] & not_timed_out
    is_nt   = df["is_dest_node_type_comparison"]  & not_timed_out

    df["chosen_community_is_X"] = np.where(is_comm, (chosen_wc == "X").astype(float), np.nan)
    df["chosen_nodetype_is_B"]  = np.where(is_nt,   (chosen_dt == "B").astype(float), np.nan)

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
    cover_correct: 1 if the participant correctly judged the stimulus symmetry, 0 otherwise.
    Derived from node_symmetry_type (S/A, from demographics stimulus_type_map)
    and the configured cover task response keys.
    Missed trials (no response) count as 0, consistent with accuracy = correct / all_trials.
    """
    correct_key = df["node_symmetry_type"].map({
        "S": COVER_KEY_SYMMETRIC,
        "A": COVER_KEY_NOT_SYMMETRIC,
    })
    has_response = df["cover_response"].notna()
    df["cover_correct"] = np.where(
        has_response,
        (df["cover_response"] == correct_key).astype(float),
        0.0  # missed trials count as incorrect
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
    test = add_correct(test)
    test = add_correct_option_properties(test)
    test = add_choice_bias_variables(test)
    test = add_confidence_z(test)
    test = test[[c for c in TEST_COLS if c in test.columns]].copy()
    test.reset_index(drop=True, inplace=True)

    print(f"\nTest trials : {len(test)} rows, {test['participant_id'].nunique()} participant(s)")
    print(f"  correct defined (T1, responded): {test['correct'].notna().sum()} / {len(test)}")
    _summarise_test(test)

    # ── Learning trials ──────────────────────────────────────────────────────
    learning = raw[raw["trial_type_label"] == "learning"].copy()
    learning["responded"] = learning["cover_response"].notna()
    learning = add_cover_correct(learning)
    learning = learning[[c for c in LEARNING_COLS if c in learning.columns]].copy()
    learning.reset_index(drop=True, inplace=True)

    print(f"\nLearning trials : {len(learning)} rows")
    print(f"  response rate  : {learning['responded'].mean():.1%}")
    print(f"  cover accuracy : {learning['cover_correct'].mean():.1%} (all trials)")

    return test, learning


def _summarise_test(df: pd.DataFrame) -> None:
    print(f"  comparison_type counts:\n"
          + df["comparison_type"].value_counts().to_string().replace("^", "    "))
    if df["correct"].notna().any():
        print(f"  mean correct (T1): {df['correct'].mean():.3f}")
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
