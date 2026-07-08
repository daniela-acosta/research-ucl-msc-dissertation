"""
compute_sdt.py
--------------
Computes d' and meta-d' for T1 trials at the block level, per participant.

d'      — 2AFC formula: d' = √2 × Φ⁻¹(p_correct), loglinear-corrected.
meta-d' — MLE estimation via metadpy (Maniscalco & Lau 2012).
m_ratio — meta-d' / d': metacognitive efficiency.

Usage (from data_analysis/):
    python scripts/compute_sdt.py
    python scripts/compute_sdt.py --participant local_1199466
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from metadpy.mle import metad

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_CSV  = REPO_ROOT / "data" / "results" / "test_trials.csv"
OUT_PATH  = REPO_ROOT / "data" / "results" / "sdt_results.csv"

N_RATINGS = 4   # confidence bins per response direction (keep low given ~24 trials/block)


# ---------------------------------------------------------------------------
# d' helpers
# ---------------------------------------------------------------------------

def dprime_2afc(n_correct: int, n_total: int) -> float:
    """d' for 2AFC with loglinear correction for extreme proportions."""
    if n_total == 0:
        return np.nan
    p = (n_correct + 0.5) / (n_total + 1)
    return float(np.sqrt(2) * norm.ppf(p))


# ---------------------------------------------------------------------------
# meta-d' helpers
# ---------------------------------------------------------------------------

def confidence_to_bins(conf: pd.Series, n: int = N_RATINGS) -> pd.Series:
    """Map confidence (0–100) to integer bins 1…n (1 = lowest, n = highest)."""
    return pd.cut(
        conf.clip(0, 100),
        bins=np.linspace(0, 100, n + 1),
        labels=range(1, n + 1),
        include_lowest=True,
    ).astype(int)


def build_nR(grp: pd.DataFrame, n_ratings: int = N_RATINGS):
    """
    Build nR_S1 and nR_S2 arrays required by metadpy.

    Convention:
        S1 trial = plausible option shown on the LEFT
        S2 trial = plausible option shown on the RIGHT

    nR arrays have length 2*n_ratings, ordered from most-confident S1
    response (index 0) to most-confident S2 response (index 2*n_ratings-1).

    The elegant identity:
        plausible_is_left = (option_a_plausible == left_is_option_a)
    holds because exactly one of optionA/optionB is plausible in T1.
    """
    plausible_left = (grp["option_a_plausible"] == grp["left_is_option_a"]).values
    chose_left     = (grp["chosen_position"] == "left").values
    conf_bins      = confidence_to_bins(grp["confidence_response"], n_ratings).values

    nR_S1 = np.zeros(2 * n_ratings, dtype=int)
    nR_S2 = np.zeros(2 * n_ratings, dtype=int)

    for pl, cl, cb in zip(plausible_left, chose_left, conf_bins):
        # S1 correct response (chose left on S1 trial): index = n_ratings - cb
        # S2 correct response (chose right on S1/S2 trial): index = n_ratings - 1 + cb
        if pl:   # S1 trial
            if cl:   nR_S1[n_ratings - cb]         += 1   # correct, S1 response
            else:    nR_S1[n_ratings - 1 + cb]     += 1   # incorrect, S2 response
        else:    # S2 trial
            if not cl: nR_S2[n_ratings - 1 + cb]  += 1   # correct, S2 response
            else:      nR_S2[n_ratings - cb]       += 1   # incorrect, S1 response

    return nR_S1, nR_S2


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------

def compute_sdt(tt: pd.DataFrame) -> pd.DataFrame:
    t1 = tt[
        (tt["comparison_type"] == "T1") &
        (tt["timed_out"] == False) &
        (tt["confidence_response"].notna()) &
        (tt["confidence_timed_out"] == False)
    ].copy()

    rows = []
    for (pid, block), grp in t1.groupby(["participant_id", "block"]):
        n_total   = len(grp)
        n_correct = int(grp["accuracy"].sum())
        dp        = dprime_2afc(n_correct, n_total)

        meta_dp = np.nan
        m_ratio = np.nan
        try:
            nR_S1, nR_S2 = build_nR(grp)
            result  = metad(nR_S1=nR_S1, nR_S2=nR_S2, nRatings=N_RATINGS)
            meta_dp = float(result["meta_d"].iloc[0])
            m_ratio = (meta_dp / dp) if (not np.isnan(dp) and dp != 0) else np.nan
        except Exception as e:
            print(f"  meta-d' failed for {pid} block {block}: {e}")

        rows.append({
            "participant_id": pid,
            "block":          block,
            "n_trials":       n_total,
            "n_correct":      n_correct,
            "p_correct":      round(n_correct / n_total, 3) if n_total > 0 else np.nan,
            "d_prime":        round(dp,      3) if not np.isnan(dp)      else np.nan,
            "meta_d_prime":   round(meta_dp, 3) if not np.isnan(meta_dp) else np.nan,
            "m_ratio":        round(m_ratio, 3) if not np.isnan(m_ratio) else np.nan,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant", "-p", default=None,
                        help="Filter to a single participant_id.")
    args = parser.parse_args()

    tt = pd.read_csv(TEST_CSV)

    if args.participant:
        if args.participant not in tt["participant_id"].values:
            raise ValueError(
                f"Participant '{args.participant}' not found. "
                f"Available: {sorted(tt['participant_id'].unique().tolist())}"
            )
        tt = tt[tt["participant_id"] == args.participant]
        print(f"Filtering to participant: {args.participant}")

    results = compute_sdt(tt)

    print("\n── SDT RESULTS (T1 trials, by block) ──")
    print(results.to_string(index=False))
    print(f"\n── MEANS ACROSS BLOCKS ──")
    print(results.groupby("participant_id")[["d_prime","meta_d_prime","m_ratio"]].mean().round(3).to_string())

    suffix = f"_{args.participant}" if args.participant else ""
    out = REPO_ROOT / "data" / "results" / f"sdt_results{suffix}.csv"
    results.to_csv(out, index=False)
    print(f"\nSaved → {out}")


if __name__ == "__main__":
    main()
