"""
preprocess.py
-------------
Loads combined_raw.csv, cleans types, derives analysis variables, and outputs:

    data/results/test_trials.csv      ← 2AFC test trials  (main analysis)
    data/results/learning_trials.csv  ← cover-task trials (supplementary)

Derived variables added to test_trials:
    correct                 1/0 for T1 trials (chose plausible option); 0 for T1 timeouts; NaN for T0/T2
    confidence_z            confidence_response z-scored within each participant
    correct_dest_community            W or X — plausible option's community relation to base; NaN for T0/T2
    correct_dest_node_type            B or NB — plausible option's node type; NaN for T0/T2
    is_dest_community_comparison      True if the pair contrasts W vs X destination community
    is_dest_node_type_comparison      True if the pair contrasts B vs NB destination node type
    chosen_community_is_X             1/0 — chose X option; NaN if not a community comparison or timed out
    chosen_nodetype_is_B              1/0 — chose B destination; NaN if not a node-type comparison or timed out
    options_adjacent                  True if option_left and option_right share a graph edge
    cumulative_question_views         how many times this participant has seen this question_code
                                      up to and including the current block (1 = first exposure)
    cumulative_base_node_views        learning steps showing base_node through end of current block
    cumulative_correct_transition_views  times base→correct_dest traversed through end of current block;
                                      NaN for T0/T2; 0 for T1 where transition never appeared
    correct_transition_last_view      steps since the most recent base→correct_dest traversal (source-node
                                      indexed; 0 = source was final learning step); NaN if T0/T2 or never seen
    session_duration                  max time_elapsed (ms) for the participant across all trial types

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

# Learning walk length per block — must match CONFIG.walkLength.
WALK_LENGTH = 48

# Graph edges as frozensets — matches the adjacency list in CLAUDE.md / config.js.
GRAPH_EDGES: frozenset = frozenset({
    frozenset({"A", "B"}), frozenset({"A", "C"}), frozenset({"A", "D"}),
    frozenset({"B", "C"}), frozenset({"B", "E"}),
    frozenset({"C", "D"}),
    frozenset({"D", "G"}),
    frozenset({"E", "F"}), frozenset({"E", "H"}),
    frozenset({"F", "G"}), frozenset({"F", "H"}),
    frozenset({"G", "H"}),
})

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
    "options_adjacent",
    "cumulative_question_views",
    "cumulative_base_node_views", "cumulative_correct_transition_views",
    "correct_transition_last_view",
    "session_duration",
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


def add_question_views(df: pd.DataFrame) -> pd.DataFrame:
    """cumulative_question_views: how many times this participant has seen this question_code
    up to and including the current block (1 = first exposure, 2 = second, etc.)."""
    df = df.sort_values(["participant_id", "question_code", "block"])
    df["cumulative_question_views"] = (
        df.groupby(["participant_id", "question_code"]).cumcount() + 1
    )
    return df


def add_graph_variables(df: pd.DataFrame) -> pd.DataFrame:
    """options_adjacent: True if option_left and option_right share a graph edge."""
    df["options_adjacent"] = [
        frozenset({l, r}) in GRAPH_EDGES
        for l, r in zip(df["option_left"], df["option_right"])
    ]
    return df


def add_learning_cross_vars(test: pd.DataFrame, learning: pd.DataFrame) -> pd.DataFrame:
    """
    Cross-references test trials with the learning walk to add recency/exposure variables.

    cumulative_base_node_views: count of learning steps showing base_node in blocks 1..current.
    cumulative_correct_transition_views: count of base→correct_dest traversals in blocks 1..current.
        NaN for T0/T2; 0 for T1 when transition was never seen.
    correct_transition_last_view: steps elapsed since the source node of the most recent
        base→correct_dest traversal (measured from that source step to the final learning step
        of the current block; 0 means the source was the very last learning step).
        NaN for T0/T2 or if the transition was never seen.

    Assumes step is 0-indexed within each block (0..WALK_LENGTH-1).
    """
    lrn = learning.copy()
    lrn["_gs"] = (lrn["block"].astype(int) - 1) * WALK_LENGTH + lrn["step"].astype(int)

    # ── cumulative_base_node_views ─────────────────────────────────────────
    base_counts = (
        lrn.groupby(["participant_id", "block", "node"])
        .size()
        .reset_index(name="_n")
    )
    base_counts = base_counts.sort_values(["participant_id", "node", "block"])
    base_counts["cumulative_base_node_views"] = (
        base_counts.groupby(["participant_id", "node"])["_n"].cumsum()
    )
    test = test.merge(
        base_counts[["participant_id", "block", "node", "cumulative_base_node_views"]].rename(
            columns={"node": "base_node"}
        ),
        on=["participant_id", "block", "base_node"],
        how="left",
    )

    # ── consecutive-pair transitions (within-block only) ───────────────────
    lrn_s = lrn.sort_values(["participant_id", "block", "step"])
    lrn_s = lrn_s.assign(_nxt=lrn_s.groupby(["participant_id", "block"])["node"].shift(-1))
    trans = lrn_s.dropna(subset=["_nxt"]).copy()

    # ── correct destination node for T1 test rows ─────────────────────────
    is_a   = test["option_a_plausible"].fillna(False).astype(bool)
    is_b   = test["option_b_plausible"].fillna(False).astype(bool)
    is_t1  = is_a ^ is_b
    l_is_a = test["left_is_option_a"].fillna(False).astype(bool)
    opt_a  = np.where(l_is_a, test["option_left"],  test["option_right"])
    opt_b  = np.where(l_is_a, test["option_right"], test["option_left"])
    test["_cdest"] = pd.Series(
        np.where(is_a, opt_a, np.where(is_b, opt_b, np.nan)), index=test.index
    )

    # ── aggregate transitions per (participant, block, source, dest) ───────
    tagg = (
        trans.groupby(["participant_id", "block", "node", "_nxt"])
        .agg(_cnt=("_gs", "count"), _last=("_gs", "max"))
        .reset_index()
    )
    tagg = tagg.sort_values(["participant_id", "node", "_nxt", "block"])
    grp  = tagg.groupby(["participant_id", "node", "_nxt"])
    tagg["cumulative_correct_transition_views"] = grp["_cnt"].cumsum()
    tagg["_last_gs"] = grp["_last"].cummax()

    test = test.merge(
        tagg[["participant_id", "block", "node", "_nxt",
              "cumulative_correct_transition_views", "_last_gs"]].rename(
            columns={"node": "base_node", "_nxt": "_cdest"}
        ),
        on=["participant_id", "block", "base_node", "_cdest"],
        how="left",
    )

    # T1 + never seen → count 0; non-T1 → NaN
    test.loc[is_t1 & test["cumulative_correct_transition_views"].isna(),
             "cumulative_correct_transition_views"] = 0.0
    test.loc[~is_t1, "cumulative_correct_transition_views"] = np.nan

    # steps_since: (last 0-indexed step of block B) − global_step_of_transition_source
    end_step = test["block"].astype(int) * WALK_LENGTH - 1
    test["correct_transition_last_view"] = end_step - test["_last_gs"]
    test.loc[~is_t1, "correct_transition_last_view"] = np.nan

    test.drop(columns=["_cdest", "_last_gs"], inplace=True)
    return test


def add_session_duration(test: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """session_duration: max time_elapsed (ms) per participant across all trial types."""
    dur = (
        raw.groupby("participant_id")["time_elapsed"]
        .max()
        .reset_index(name="session_duration")
    )
    return test.merge(dur, on="participant_id", how="left")


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

    # ── Learning trials (extracted first — needed for cross-reference variables) ──
    learning_raw = raw[raw["trial_type_label"] == "learning"].copy()
    learning_raw["responded"] = learning_raw["cover_response"].notna()
    learning_raw = add_cover_correct(learning_raw)

    # ── Test trials ──────────────────────────────────────────────────────────
    test = raw[raw["trial_type_label"] == "test"].copy()
    test = add_correct(test)
    test = add_correct_option_properties(test)
    test = add_choice_bias_variables(test)
    test = add_question_views(test)
    test = add_graph_variables(test)
    test = add_learning_cross_vars(test, learning_raw)
    test = add_session_duration(test, raw)
    test = add_confidence_z(test)
    test = test[[c for c in TEST_COLS if c in test.columns]].copy()
    test.reset_index(drop=True, inplace=True)

    print(f"\nTest trials : {len(test)} rows, {test['participant_id'].nunique()} participant(s)")
    print(f"  correct defined (T1, responded): {test['correct'].notna().sum()} / {len(test)}")
    _summarise_test(test)

    # ── Learning trials (finalised) ───────────────────────────────────────────
    learning = learning_raw[[c for c in LEARNING_COLS if c in learning_raw.columns]].copy()
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
