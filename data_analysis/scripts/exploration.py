import argparse
import subprocess

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats

parser = argparse.ArgumentParser(description="Exploratory plots for the graph learning experiment.")
parser.add_argument(
    "--participant", "-p",
    default=None,
    help="participant_id to filter on. Omit to plot all participants combined."
)
args = parser.parse_args()

# Canonical category order (by category number 1–9) for consistent x-axis / legend.
CAT_ORDER = [
    'NB1WB__NB2XB',   # 1
    'NB1WNB__NB2XB',  # 2
    'NB1WB__NB1WNB',  # 3
    'B2WB__B2XNB',    # 4
    'B1WNB__B2WB',    # 5
    'B1WNB__B2XNB',   # 6
    'B1XB__B2WB',     # 7
    'B1XB__B2XNB',    # 8
    'B1WNB__B1XB',    # 9
]
# T1-only subset (categories 1, 2, 5, 6, 7, 8) in the same order.
T1_ORDER = [t for t in CAT_ORDER if t in {
    'NB1WB__NB2XB', 'NB1WNB__NB2XB',
    'B1WNB__B2WB',  'B1WNB__B2XNB',
    'B1XB__B2WB',   'B1XB__B2XNB',
}]

ct = pd.read_csv("../data/results/learning_trials.csv")
tt = pd.read_csv("../data/results/test_trials.csv")

# Older data collections lack confidence_slider_start (logged from a later build).
# Fall back to 50 (slider midpoint) so downstream analyses degrade gracefully.
if "confidence_slider_start" not in tt.columns:
    tt["confidence_slider_start"] = 50
else:
    tt["confidence_slider_start"] = tt["confidence_slider_start"].fillna(50)

if args.participant:
    if args.participant not in ct["participant_id"].values and \
       args.participant not in tt["participant_id"].values:
        raise ValueError(
            f"Participant '{args.participant}' not found. "
            f"Available: {sorted(ct['participant_id'].unique().tolist())}"
        )
    ct = ct[ct["participant_id"] == args.participant]
    tt = tt[tt["participant_id"] == args.participant]
    print(f"Filtering to participant: {args.participant}")
else:
    print(f"Showing all participants: {sorted(ct['participant_id'].unique().tolist())}")

# ── Cumulative transition counts from learning phases ─────────────────────────
# trans_raw: every consecutive (src, dst) pair within each block.
# tc: cumulative count per (participant, block, src, dst) — so at block B the
#     count reflects all learning steps from blocks 1 through B.
_ct_s = ct.sort_values(["participant_id", "block", "step"]).copy()
_ct_s["next_node"] = _ct_s.groupby(["participant_id", "block"])["node"].shift(-1)
trans_raw = (
    _ct_s.dropna(subset=["next_node"])
    [["participant_id", "block", "node", "next_node"]]
    .rename(columns={"node": "src", "next_node": "dst"})
)
_tc_cnt = (
    trans_raw.groupby(["participant_id", "block", "src", "dst"])
    .size().reset_index(name="n_block")
    .sort_values(["participant_id", "src", "dst", "block"])
)
_tc_cnt["n_cumul"] = _tc_cnt.groupby(["participant_id", "src", "dst"])["n_block"].cumsum()
tc = _tc_cnt[["participant_id", "block", "src", "dst", "n_cumul"]]

# Per-trial cumulative counts for plausible and implausible transitions (T1 only).
# The candidates CSV has both orderings of optionA/B within each pair_tag, so we
# can't assume optionA is always the plausible option — use option_a_plausible instead.
# plausible_is_left = (option_a_plausible == left_is_option_a):
#   True when optionA is plausible and is on the left, OR optionA is implausible
#   and is on the right (meaning optionB, the plausible one, is on the left).
_t1_early = tt[(tt["comparison_type"] == "T1") & (tt["timed_out"] == False)].copy()
_plaus_left_e = (
    _t1_early["option_a_plausible"].astype(bool) == _t1_early["left_is_option_a"].astype(bool)
)
_t1_early["_plaus_node"]   = _t1_early["option_left"].where(_plaus_left_e,  _t1_early["option_right"])
_t1_early["_implaus_node"] = _t1_early["option_right"].where(_plaus_left_e, _t1_early["option_left"])
_t1_early = _t1_early.merge(
    tc.rename(columns={"src": "base_node", "dst": "_pn", "n_cumul": "trans_plausible"}),
    left_on=["participant_id", "block", "base_node", "_plaus_node"],
    right_on=["participant_id", "block", "base_node", "_pn"], how="left"
).drop(columns="_pn")
_t1_early["trans_plausible"] = _t1_early["trans_plausible"].fillna(0).astype(int)
_t1_early = _t1_early.merge(
    tc.rename(columns={"src": "base_node", "dst": "_in", "n_cumul": "trans_implausible"}),
    left_on=["participant_id", "block", "base_node", "_implaus_node"],
    right_on=["participant_id", "block", "base_node", "_in"], how="left"
).drop(columns="_in")
_t1_early["trans_implausible"] = _t1_early["trans_implausible"].fillna(0).astype(int)

# Suffix appended to output filenames — blank for combined, participant id for single.
file_suffix = f"_{args.participant}" if args.participant else ""
# Title tag for plot supertitles.
title_tag = f"Participant: {args.participant}" if args.participant else "All Participants"

print(tt.head())

# GLOBAL
# COVER TASK
ct_res = (
    ct.groupby("participant_id")
    .agg(
        response_rate=("responded", "mean"),
        mean_rt=("cover_rt", "mean"),
        accuracy=("cover_correct", "mean"),
    )
    .round(3)
    .reset_index()
)

# 2AFC + CONFIDENCE (exclude 2AFC timeouts for RT/accuracy; confidence has its own timeout)
tt_responded = tt[tt["timed_out"] == False]
tt_res = (
    tt_responded.groupby("participant_id")
    .agg(
        timeout_rate=("timed_out", "mean"),        # proportion timed out overall
        mean_rt=("rt", "mean"),
        correct_t1=("correct", "mean"),            # NaN for T0/T2, so mean is T1-only
        mean_confidence=("confidence_response", "mean"),
        conf_mean_rt=("confidence_rt", "mean"),
    )
    .round(3)
    .reset_index()
)
# timeout_rate should come from all trials, not just responded ones
tt_res["timeout_rate"] = tt.groupby("participant_id")["timed_out"].mean().round(3).values

def with_totals(df, id_col="participant_id"):
    means = df.select_dtypes("number").mean().round(3)
    return pd.concat([df, pd.DataFrame([{id_col: "MEAN", **means}])], ignore_index=True)

print("\n── LEARNING (cover task) ──")
print(with_totals(ct_res).to_string(index=False))

print("\n── TEST (2AFC + confidence) ──")
print(with_totals(tt_res).to_string(index=False))

# ── RT coefficient of variation (SD / mean) per participant ──────────────────
# CV flags abnormal response patterns: very low CV suggests button-mashing
# (implausibly consistent RTs); very high CV suggests disengagement.
_ct_rt = (
    ct[ct["responded"] == True]
    .groupby("participant_id")["cover_rt"]
    .agg(mean_rt="mean", sd_rt="std", median_rt="median", min_rt="min", max_rt="max")
    .round(1)
    .reset_index()
)
_ct_rt["cv"] = (_ct_rt["sd_rt"] / _ct_rt["mean_rt"]).round(3)

_tt_rt = (
    tt[tt["timed_out"] == False]
    .groupby("participant_id")["rt"]
    .agg(mean_rt="mean", sd_rt="std", median_rt="median", min_rt="min", max_rt="max")
    .round(1)
    .reset_index()
)
_tt_rt["cv"] = (_tt_rt["sd_rt"] / _tt_rt["mean_rt"]).round(3)

_conf_rt = (
    tt[tt["confidence_timed_out"] == False]
    .groupby("participant_id")["confidence_rt"]
    .agg(mean_rt="mean", sd_rt="std", median_rt="median", min_rt="min", max_rt="max")
    .round(1)
    .reset_index()
)
_conf_rt["cv"] = (_conf_rt["sd_rt"] / _conf_rt["mean_rt"]).round(3)

_conf_resp = (
    tt[tt["confidence_timed_out"] == False]
    .groupby("participant_id")["confidence_response"]
    .agg(mean_resp="mean", sd_resp="std", median_resp="median", min_resp="min", max_resp="max")
    .round(1)
    .reset_index()
)
_conf_resp["cv"] = (_conf_resp["sd_resp"] / _conf_resp["mean_resp"]).round(3)

rt_cv = (
    _ct_rt.rename(columns={"mean_rt": "ct_mean", "sd_rt": "ct_sd", "median_rt": "ct_median", "cv": "ct_cv", "min_rt": "ct_min", "max_rt": "ct_max"})
    .merge(
        _tt_rt.rename(columns={"mean_rt": "tt_mean", "sd_rt": "tt_sd", "median_rt": "tt_median", "cv": "tt_cv", "min_rt": "tt_min", "max_rt": "tt_max"}),
        on="participant_id", how="outer"
    )
    .merge(
        _conf_rt.rename(columns={"mean_rt": "conf_rt_mean", "sd_rt": "conf_rt_sd", "median_rt": "conf_rt_median", "cv": "conf_rt_cv", "min_rt": "conf_rt_min", "max_rt": "conf_rt_max"}),
        on="participant_id", how="outer"
    )
    .merge(
        _conf_resp.rename(columns={"mean_resp": "conf_resp_mean", "sd_resp": "conf_resp_sd", "median_resp": "conf_resp_median", "cv": "conf_resp_cv", "min_resp": "conf_resp_min", "max_resp": "conf_resp_max"}),
        on="participant_id", how="outer"
    )
)
print("\n── RT COEFFICIENT OF VARIATION (SD / mean)  [timed-out trials excluded] ──")

_cv_sections = [
    ("Cover task RT (ms)",          ["ct_mean",        "ct_sd",        "ct_median",        "ct_min",        "ct_max",        "ct_cv"]),
    ("2AFC RT (ms)",                 ["tt_mean",        "tt_sd",        "tt_median",        "tt_min",        "tt_max",        "tt_cv"]),
    ("Confidence RT (ms)",           ["conf_rt_mean",   "conf_rt_sd",   "conf_rt_median",   "conf_rt_min",   "conf_rt_max",   "conf_rt_cv"]),
    ("Confidence response (0–100)",  ["conf_resp_mean", "conf_resp_sd", "conf_resp_median", "conf_resp_min", "conf_resp_max", "conf_resp_cv"]),
]
_clean_cols = ["mean", "sd", "median", "min", "max", "cv"]

for title, cols in _cv_sections:
    sub = with_totals(rt_cv[["participant_id"] + cols].copy())
    sub.columns = ["participant_id"] + _clean_cols
    print(f"\n  {title}")
    print(sub.to_string(index=False))

# ── Confidence response vs slider start position correlation ─────────────────
# A high correlation would suggest participants are anchoring on the random
# start rather than genuinely rating their confidence.
# Note: data collected before slider_start logging use a fallback of 50 —
# those participants will show near-zero correlation by construction.
_conf_rows = tt[
    (tt["timed_out"] == False) &
    tt["confidence_response"].notna() &
    tt["confidence_slider_start"].notna()
].copy()

_conf_corr_rows = []
for pid, grp in _conf_rows.groupby("participant_id"):
    if len(grp) >= 3:
        r, p = stats.pearsonr(grp["confidence_slider_start"], grp["confidence_response"])
        _conf_corr_rows.append({
            "participant_id": pid,
            "n":              len(grp),
            "r":              round(r, 3),
            "p":              round(p, 3),
        })
_conf_corr_df = pd.DataFrame(_conf_corr_rows)
print("\n── CONFIDENCE RESPONSE vs SLIDER START (Pearson r, per participant) ──")
if len(_conf_corr_df) > 0:
    print(with_totals(_conf_corr_df).to_string(index=False))
    if len(_conf_rows) >= 3:
        r_all, p_all = stats.pearsonr(
            _conf_rows["confidence_slider_start"], _conf_rows["confidence_response"]
        )
        print(f"\nPooled across all participants: r = {r_all:.3f}, p = {p_all:.3f}  (n = {len(_conf_rows)})")
else:
    print("  Not enough data (need ≥ 3 confidence responses per participant).")

# BY QUESTION TYPE (averaged across all participants and blocks)
_trans_t1_by_cat = (
    _t1_early.groupby("comparison_pair_tag")
    .agg(n_plausible=("trans_plausible", "mean"), n_implausible=("trans_implausible", "mean"))
    .round(2).reset_index()
)
qtype_res = (
    tt[tt["timed_out"] == False]
    .groupby(["comparison_type", "category", "comparison_pair_tag"])
    .agg(
        correct         =("correct",             "mean"),  # NaN for T0/T2
        mean_rt         =("rt",                  "mean"),
        mean_confidence =("confidence_response", "mean"),
    )
    .round(3)
    .reset_index()
    .sort_values("category")
    .rename(columns={"comparison_pair_tag": "pair_tag", "comparison_type": "type",
                     "mean_rt": "rt", "mean_confidence": "confidence"})
    .merge(_trans_t1_by_cat.rename(columns={"comparison_pair_tag": "pair_tag"}),
           on="pair_tag", how="left")
)
print("\n── BY QUESTION TYPE (all participants, all blocks) ──")
print(qtype_res.to_string(index=False))

type_res = (
    tt[tt["timed_out"] == False]
    .groupby("comparison_type")
    .agg(
        correct         =("correct",             "mean"),
        mean_rt         =("rt",                  "mean"),
        mean_confidence =("confidence_response", "mean"),
    )
    .round(3)
    .reset_index()
    .rename(columns={"comparison_type": "type", "mean_rt": "rt", "mean_confidence": "confidence"})
    .sort_values("type")
)
print("\n── BY COMPARISON TYPE (T0 / T1 / T2) ──")
print(type_res.to_string(index=False))

node_res = (
    tt[tt["timed_out"] == False]
    .groupby("base_node")
    .agg(
        correct         =("correct",             "mean"),
        mean_rt         =("rt",                  "mean"),
        mean_confidence =("confidence_response", "mean"),
    )
    .round(3)
    .reset_index()
    .rename(columns={"base_node": "node", "mean_rt": "rt", "mean_confidence": "confidence"})
    .sort_values("node")
)
print("\n── BY BASE NODE ──")
print(node_res.to_string(index=False))

base_fractal_res = (
    tt[tt["timed_out"] == False]
    .groupby("base_fractal")
    .agg(
        correct         =("correct",             "mean"),
        mean_rt         =("rt",                  "mean"),
        mean_confidence =("confidence_response", "mean"),
    )
    .round(3)
    .reset_index()
    .rename(columns={"base_fractal": "fractal", "mean_rt": "rt", "mean_confidence": "confidence"})
    .sort_values("fractal")
)
print("\n── BY BASE FRACTAL ──")
print(base_fractal_res.to_string(index=False))

dest_fractal_res = (
    tt[tt["timed_out"] == False]
    .groupby("chosen_fractal")
    .agg(
        correct         =("correct",             "mean"),
        mean_rt         =("rt",                  "mean"),
        mean_confidence =("confidence_response", "mean"),
    )
    .round(3)
    .reset_index()
    .rename(columns={"chosen_fractal": "fractal", "mean_rt": "rt", "mean_confidence": "confidence"})
    .sort_values("fractal")
)
print("\n── BY CHOSEN (DESTINATION) FRACTAL ──")
print(dest_fractal_res.to_string(index=False))

tt_resp = tt[tt["timed_out"] == False].copy()
tt_resp["base_sym_type"] = tt_resp["base_fractal"].str.extract(r"_(S|A)\.png")

BOUNDARY = {"B", "D", "E", "G"}
tt_resp["base_node_type"] = tt_resp["base_node"].map(lambda n: "B" if n in BOUNDARY else "NB")

sym_res = (
    tt_resp.groupby("base_sym_type")
    .agg(
        correct         =("correct",             "mean"),
        mean_rt         =("rt",                  "mean"),
        mean_confidence =("confidence_response", "mean"),
    )
    .round(3)
    .reset_index()
    .rename(columns={"base_sym_type": "type", "mean_rt": "rt", "mean_confidence": "confidence"})
)
print("\n── BY BASE FRACTAL TYPE (S vs A) ──")
print(sym_res.to_string(index=False))

nb_res = (
    tt_resp.groupby("base_node_type")
    .agg(
        correct         =("correct",             "mean"),
        mean_rt         =("rt",                  "mean"),
        mean_confidence =("confidence_response", "mean"),
    )
    .round(3)
    .reset_index()
    .rename(columns={"base_node_type": "type", "mean_rt": "rt", "mean_confidence": "confidence"})
    .sort_values("type")
)
print("\n── BY BASE NODE TYPE (B vs NB) ──")
print(nb_res.to_string(index=False))

# Node visit counts from learning phase — sanity check for random walk uniformity.
# Expected: ~13 visits per node (104 total steps / 8 nodes) if walk is uniform.
node_visit_res = (
    ct.groupby(["participant_id", "node"])
    .size().reset_index(name="n_visits")
    .groupby("node")["n_visits"]
    .agg(mean="mean", std="std")
    .round(2)
    .reset_index()
    .sort_values("node")
)
BOUNDARY = {"B", "D", "E", "G"}
node_visit_res["type"] = node_visit_res["node"].map(lambda n: "B" if n in BOUNDARY else "NB")
print("\n── NODE VISIT COUNTS (learning phase, all blocks, expected ≈13 per node) ──")
print(node_visit_res.to_string(index=False))

# BY BLOCK
# COVER TASK
ct_res_block = (
    ct[ct["responded"]]
    .groupby(["participant_id", "block"])
    .agg(mean_rt=("cover_rt", "mean"), accuracy=("cover_correct", "mean"))
    .reset_index()
)


# 2AFC & CONFIDENCE — global (all question types)
tt_res_block = (
    tt[tt["timed_out"] == False]
    .groupby(["participant_id", "block"])
    .agg(
        mean_rt        =("rt",                  "mean"),
        correct        =("correct",             "mean"),   # NaN for T0/T2, so mean is T1-only
        mean_confidence=("confidence_response", "mean"),
        conf_mean_rt   =("confidence_rt",       "mean"),
    )
    .reset_index()
)

# T1-only confidence by block
tt_res_block_t1 = (
    tt[(tt["timed_out"] == False) & (tt["comparison_type"] == "T1")]
    .groupby(["participant_id", "block"])
    .agg(mean_confidence=("confidence_response", "mean"))
    .reset_index()
)

# ── axis limit helper ────────────────────────────────────────────────────────
def ylim(*series, pad=0.07):
    """Return (min, max) across all provided series, padded by pad * range."""
    import numpy as np
    vals = pd.concat([s.dropna() for s in series])
    lo, hi = vals.min(), vals.max()
    margin = (hi - lo) * pad if hi != lo else max(abs(lo), 0.1) * pad
    return (lo - margin, hi + margin)

# ── by-block axis limits (computed from data) ────────────────────────────────
ct_acc_ylim  = ylim(ct_res_block["accuracy"])
tt_acc_ylim  = ylim(tt_res_block["correct"])
tt_conf_ylim = ylim(tt_res_block["mean_confidence"], tt_res_block_t1["mean_confidence"])

# ── colors ──────────────────────────────────────────────────────────────────
color_rt   = "steelblue"
color_acc  = "darkorange"
color_conf = "mediumseagreen"
color_crt  = "mediumpurple"

fig, (ax_ct, ax_2afc, ax_conf, ax_conf_t1) = plt.subplots(1, 4, figsize=(22, 5))

# Panel 1 — cover task RT + accuracy
ax_ct2 = ax_ct.twinx()
sns.lineplot(data=ct_res_block, x="block", y="mean_rt",  marker="o", ax=ax_ct,  color=color_rt)
sns.lineplot(data=ct_res_block, x="block", y="accuracy", marker="o", ax=ax_ct2, color=color_acc)
for _, g in ct_res_block.groupby("participant_id"):
    ax_ct2.scatter(g["block"], g["accuracy"], alpha=0.35, s=18, color=color_acc, zorder=2)
ax_ct.set_ylabel("Mean RT (ms)", color=color_rt)
ax_ct.tick_params(axis="y", labelcolor=color_rt)
ax_ct2.set_ylabel("Accuracy", color=color_acc)
ax_ct2.tick_params(axis="y", labelcolor=color_acc)
ax_ct2.set_ylim(ct_acc_ylim)
ax_ct.set_title("Cover Task")
ax_ct.set_xticks([1, 2, 3, 4])
ax_ct.set_xlabel("Block")

# Panel 2 — 2AFC RT + accuracy
ax_2afc2 = ax_2afc.twinx()
sns.lineplot(data=tt_res_block, x="block", y="mean_rt",  marker="o", ax=ax_2afc,  color=color_rt)
sns.lineplot(data=tt_res_block, x="block", y="correct", marker="o", ax=ax_2afc2, color=color_acc)
for _, g in tt_res_block.groupby("participant_id"):
    ax_2afc2.scatter(g["block"], g["correct"], alpha=0.35, s=18, color=color_acc, zorder=2)
ax_2afc.set_ylabel("Mean RT (ms)", color=color_rt)
ax_2afc.tick_params(axis="y", labelcolor=color_rt)
ax_2afc2.set_ylabel("Accuracy (T1 only)", color=color_acc)
ax_2afc2.tick_params(axis="y", labelcolor=color_acc)
ax_2afc2.set_ylim(tt_acc_ylim)
ax_2afc.set_title("2AFC")
ax_2afc.set_xticks([1, 2, 3, 4])
ax_2afc.set_xlabel("Block")

# Panel 3 — confidence response + confidence RT
ax_conf2 = ax_conf.twinx()
sns.lineplot(data=tt_res_block, x="block", y="mean_confidence", marker="o", ax=ax_conf,  color=color_conf)
for _, g in tt_res_block.groupby("participant_id"):
    ax_conf.scatter(g["block"], g["mean_confidence"], alpha=0.35, s=18, color=color_conf, zorder=2)
sns.lineplot(data=tt_res_block, x="block", y="conf_mean_rt",    marker="o", ax=ax_conf2, color=color_crt)
ax_conf.set_ylabel("Mean Confidence (0–100)", color=color_conf)
ax_conf.tick_params(axis="y", labelcolor=color_conf)
ax_conf2.set_ylabel("Confidence RT (ms)", color=color_crt)
ax_conf2.tick_params(axis="y", labelcolor=color_crt)
ax_conf.set_ylim(tt_conf_ylim)
ax_conf.set_title("Confidence (all)")
ax_conf.set_xticks([1, 2, 3, 4])
ax_conf.set_xlabel("Block")

# Panel 4 — T1-only confidence by block
sns.lineplot(data=tt_res_block_t1, x="block", y="mean_confidence", marker="o",
             ax=ax_conf_t1, color=color_conf)
for _, g in tt_res_block_t1.groupby("participant_id"):
    ax_conf_t1.scatter(g["block"], g["mean_confidence"], alpha=0.35, s=18, color=color_conf, zorder=2)
ax_conf_t1.set_ylabel("Mean Confidence (0–100)", color=color_conf)
ax_conf_t1.tick_params(axis="y", labelcolor=color_conf)
ax_conf_t1.set_ylim(tt_conf_ylim)
ax_conf_t1.set_title("Confidence (T1 only)")
ax_conf_t1.set_xticks([1, 2, 3, 4])
ax_conf_t1.set_xlabel("Block")

plt.suptitle(f"By Block — {title_tag}", y=1.01)
plt.tight_layout()
out = f"../data/results/exploration_by_block{file_suffix}.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
subprocess.run(["open", out])

# ── Accuracy gain across blocks: significance test (T1 trials) ────────────────
# Per-participant slope (block → accuracy) via linear regression, then
# one-sample t-test on the distribution of slopes against zero.
_t1_blk = (
    tt[(tt["comparison_type"] == "T1") & (tt["timed_out"] == False)]
    .groupby(["participant_id", "block"])["correct"]
    .mean().reset_index()
)
_slopes = []
for pid, grp in _t1_blk.groupby("participant_id"):
    grp = grp.sort_values("block")
    res = stats.linregress(grp["block"], grp["correct"])
    _slopes.append({
        "participant_id": pid,
        "slope":          round(res.slope,    4),
        "intercept":      round(res.intercept, 3),
        "r":              round(res.rvalue,    3),
        "p_within":       round(res.pvalue,   3),
    })
_slopes_df = pd.DataFrame(_slopes)
print("\n── ACCURACY GAIN ACROSS BLOCKS — PER-PARTICIPANT SLOPES (T1) ──")
print(_slopes_df.to_string(index=False))
if len(_slopes_df) >= 2:
    _t, _p = stats.ttest_1samp(_slopes_df["slope"], 0)
    print(f"\nMean slope = {_slopes_df['slope'].mean():.4f} accuracy/block")
    print(f"One-sample t-test (H0: slope = 0): t({len(_slopes_df)-1}) = {_t:.3f}, p = {_p:.3f}")
else:
    print(f"\nSlope = {_slopes_df['slope'].iloc[0]:.4f} accuracy/block  (n=1, no group test)")

# Split by comparison type
t1 = tt[tt["comparison_type"] == "T1"].copy()
t0 = tt[tt["comparison_type"] == "T0"].copy()
t2 = tt[tt["comparison_type"] == "T2"].copy()

t1_resp = t1[t1["timed_out"] == False]
t0_resp = t0[t0["timed_out"] == False]
t2_resp = t2[t2["timed_out"] == False]

T0_ORDER = ['B2WB__B2XNB']
T2_ORDER = ['NB1WB__NB1WNB', 'B1WNB__B1XB']

# ── T1 aggregations ──────────────────────────────────────────────────────────
acc_by_cat = (
    t1.groupby(["category", "comparison_pair_tag"])["correct"]
    .mean().reset_index().sort_values("category")
)
acc_by_cat_block = t1.groupby(["comparison_pair_tag", "block"])["correct"].mean().reset_index()
rt_t1_global     = t1_resp.groupby("comparison_pair_tag")["rt"].mean().reset_index()
rt_t1_block      = t1_resp.groupby(["comparison_pair_tag", "block"])["rt"].mean().reset_index()
conf_t1_global   = t1_resp.groupby("comparison_pair_tag")["confidence_response"].mean().reset_index()
conf_t1_block    = t1_resp.groupby(["comparison_pair_tag", "block"])["confidence_response"].mean().reset_index()

# ── T0 aggregations ──────────────────────────────────────────────────────────
rt_t0_global   = t0_resp.groupby("comparison_pair_tag")["rt"].mean().reset_index()
rt_t0_block    = t0_resp.groupby(["comparison_pair_tag", "block"])["rt"].mean().reset_index()
conf_t0_global = t0_resp.groupby("comparison_pair_tag")["confidence_response"].mean().reset_index()
conf_t0_block  = t0_resp.groupby(["comparison_pair_tag", "block"])["confidence_response"].mean().reset_index()

# ── T2 aggregations ──────────────────────────────────────────────────────────
rt_t2_global   = t2_resp.groupby("comparison_pair_tag")["rt"].mean().reset_index()
rt_t2_block    = t2_resp.groupby(["comparison_pair_tag", "block"])["rt"].mean().reset_index()
conf_t2_global = t2_resp.groupby("comparison_pair_tag")["confidence_response"].mean().reset_index()
conf_t2_block  = t2_resp.groupby(["comparison_pair_tag", "block"])["confidence_response"].mean().reset_index()

# ── category-level axis limits (computed from data) ──────────────────────────
_acc_lo, _acc_hi = ylim(acc_by_cat["correct"], acc_by_cat_block["correct"])
cat_acc_ylim  = (min(_acc_lo, 0.45), _acc_hi)   # always show the 0.5 chance line
cat_rt_ylim   = ylim(
    rt_t1_global["rt"],   rt_t1_block["rt"],
    rt_t0_global["rt"],   rt_t0_block["rt"],
    rt_t2_global["rt"],   rt_t2_block["rt"],
)
cat_conf_ylim = ylim(
    conf_t1_global["confidence_response"], conf_t1_block["confidence_response"],
    conf_t0_global["confidence_response"], conf_t0_block["confidence_response"],
    conf_t2_global["confidence_response"], conf_t2_block["confidence_response"],
)

# ── fig_t1: T1 — Accuracy + RT + Confidence (3×2) ───────────────────────────
fig_t1, axes_t1 = plt.subplots(3, 2, figsize=(16, 14))

sns.barplot(data=acc_by_cat, x="comparison_pair_tag", y="correct",
            ax=axes_t1[0, 0], color=color_acc, order=T1_ORDER)
axes_t1[0, 0].axhline(0.5, color="black", linestyle="--", linewidth=0.8)
axes_t1[0, 0].set_ylim(cat_acc_ylim)
axes_t1[0, 0].set_title("Accuracy by Category (T1)")
axes_t1[0, 0].set_xlabel("")
axes_t1[0, 0].set_ylabel("Accuracy")
axes_t1[0, 0].tick_params(axis="x", rotation=30)

sns.lineplot(data=acc_by_cat_block, x="block", y="correct",
             hue="comparison_pair_tag", hue_order=T1_ORDER, marker="o", ax=axes_t1[0, 1])
axes_t1[0, 1].axhline(0.5, color="black", linestyle="--", linewidth=0.8)
axes_t1[0, 1].set_ylim(cat_acc_ylim)
axes_t1[0, 1].set_title("Accuracy across Blocks (T1)")
axes_t1[0, 1].set_xlabel("Block")
axes_t1[0, 1].set_ylabel("Accuracy")
axes_t1[0, 1].set_xticks([1, 2, 3, 4])
axes_t1[0, 1].legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)

sns.barplot(data=rt_t1_global, x="comparison_pair_tag", y="rt",
            ax=axes_t1[1, 0], color=color_rt, order=T1_ORDER)
axes_t1[1, 0].set_ylim(cat_rt_ylim)
axes_t1[1, 0].set_title("RT by Category (T1)")
axes_t1[1, 0].set_xlabel("")
axes_t1[1, 0].set_ylabel("Mean RT (ms)")
axes_t1[1, 0].tick_params(axis="x", rotation=30)

sns.lineplot(data=rt_t1_block, x="block", y="rt",
             hue="comparison_pair_tag", hue_order=T1_ORDER, marker="o", ax=axes_t1[1, 1])
axes_t1[1, 1].set_ylim(cat_rt_ylim)
axes_t1[1, 1].set_title("RT across Blocks (T1)")
axes_t1[1, 1].set_xlabel("Block")
axes_t1[1, 1].set_ylabel("Mean RT (ms)")
axes_t1[1, 1].set_xticks([1, 2, 3, 4])
axes_t1[1, 1].legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)

sns.barplot(data=conf_t1_global, x="comparison_pair_tag", y="confidence_response",
            ax=axes_t1[2, 0], color=color_conf, order=T1_ORDER)
axes_t1[2, 0].set_ylim(cat_conf_ylim)
axes_t1[2, 0].set_title("Confidence by Category (T1)")
axes_t1[2, 0].set_xlabel("Category")
axes_t1[2, 0].set_ylabel("Mean Confidence (0–100)")
axes_t1[2, 0].tick_params(axis="x", rotation=30)

sns.lineplot(data=conf_t1_block, x="block", y="confidence_response",
             hue="comparison_pair_tag", hue_order=T1_ORDER, marker="o", ax=axes_t1[2, 1])
axes_t1[2, 1].set_ylim(cat_conf_ylim)
axes_t1[2, 1].set_title("Confidence across Blocks (T1)")
axes_t1[2, 1].set_xlabel("Block")
axes_t1[2, 1].set_ylabel("Mean Confidence (0–100)")
axes_t1[2, 1].set_xticks([1, 2, 3, 4])
axes_t1[2, 1].legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)

plt.suptitle(f"T1 Trials — Accuracy, RT & Confidence by Category — {title_tag}", y=1.01)
plt.tight_layout()
out = f"../data/results/exploration_by_category_T1{file_suffix}.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
subprocess.run(["open", out])

# ── fig_t1_ci: T1 — Confidence & RT split by Correct vs Incorrect ────────────
t1_resp_ci = t1_resp.copy()
t1_resp_ci["correct_label"] = t1_resp_ci["correct"].map({1.0: "Correct", 0.0: "Incorrect"})

ci_conf_cat   = (t1_resp_ci.groupby(["correct_label", "comparison_pair_tag"])
                 ["confidence_response"].mean().reset_index())
ci_conf_block = (t1_resp_ci.groupby(["correct_label", "block"])
                 ["confidence_response"].mean().reset_index())
ci_rt_cat     = (t1_resp_ci.groupby(["correct_label", "comparison_pair_tag"])
                 ["rt"].mean().reset_index())
ci_rt_block   = (t1_resp_ci.groupby(["correct_label", "block"])
                 ["rt"].mean().reset_index())

ci_palette  = {"Correct": "seagreen", "Incorrect": "salmon"}
ci_hue_order = ["Correct", "Incorrect"]

ci_conf_ylim = ylim(ci_conf_cat["confidence_response"], ci_conf_block["confidence_response"])
ci_rt_ylim   = ylim(ci_rt_cat["rt"], ci_rt_block["rt"])

fig_ci, axes_ci = plt.subplots(3, 2, figsize=(16, 14))

# Row 1 — overall accuracy (context; same as T1 category figure)
sns.barplot(data=acc_by_cat, x="comparison_pair_tag", y="correct",
            ax=axes_ci[0, 0], color=color_acc, order=T1_ORDER)
axes_ci[0, 0].axhline(0.5, color="black", linestyle="--", linewidth=0.8)
axes_ci[0, 0].set_ylim(cat_acc_ylim)
axes_ci[0, 0].set_title("Accuracy by Category (T1)")
axes_ci[0, 0].set_xlabel("")
axes_ci[0, 0].set_ylabel("Accuracy")
axes_ci[0, 0].tick_params(axis="x", rotation=30)

sns.lineplot(data=acc_by_cat_block, x="block", y="correct",
             hue="comparison_pair_tag", hue_order=T1_ORDER, marker="o", ax=axes_ci[0, 1])
axes_ci[0, 1].axhline(0.5, color="black", linestyle="--", linewidth=0.8)
axes_ci[0, 1].set_ylim(cat_acc_ylim)
axes_ci[0, 1].set_title("Accuracy across Blocks (T1)")
axes_ci[0, 1].set_xlabel("Block")
axes_ci[0, 1].set_ylabel("Accuracy")
axes_ci[0, 1].set_xticks([1, 2, 3, 4])
axes_ci[0, 1].legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)

# Row 2 — confidence by correct / incorrect
sns.barplot(data=ci_conf_cat, x="comparison_pair_tag", y="confidence_response",
            hue="correct_label", hue_order=ci_hue_order, palette=ci_palette,
            ax=axes_ci[1, 0], order=T1_ORDER)
axes_ci[1, 0].set_ylim(ci_conf_ylim)
axes_ci[1, 0].set_title("Confidence by Category — Correct vs Incorrect (T1)")
axes_ci[1, 0].set_xlabel("")
axes_ci[1, 0].set_ylabel("Mean Confidence (0–100)")
axes_ci[1, 0].tick_params(axis="x", rotation=30)
axes_ci[1, 0].legend(title="Response")

sns.lineplot(data=ci_conf_block, x="block", y="confidence_response",
             hue="correct_label", hue_order=ci_hue_order, palette=ci_palette,
             marker="o", ax=axes_ci[1, 1])
axes_ci[1, 1].set_ylim(ci_conf_ylim)
axes_ci[1, 1].set_title("Confidence across Blocks — Correct vs Incorrect (T1)")
axes_ci[1, 1].set_xlabel("Block")
axes_ci[1, 1].set_ylabel("Mean Confidence (0–100)")
axes_ci[1, 1].set_xticks([1, 2, 3, 4])
axes_ci[1, 1].legend(title="Response")

# Row 3 — RT by correct / incorrect
sns.barplot(data=ci_rt_cat, x="comparison_pair_tag", y="rt",
            hue="correct_label", hue_order=ci_hue_order, palette=ci_palette,
            ax=axes_ci[2, 0], order=T1_ORDER)
axes_ci[2, 0].set_ylim(ci_rt_ylim)
axes_ci[2, 0].set_title("RT by Category — Correct vs Incorrect (T1)")
axes_ci[2, 0].set_xlabel("Category")
axes_ci[2, 0].set_ylabel("Mean RT (ms)")
axes_ci[2, 0].tick_params(axis="x", rotation=30)
axes_ci[2, 0].legend(title="Response")

sns.lineplot(data=ci_rt_block, x="block", y="rt",
             hue="correct_label", hue_order=ci_hue_order, palette=ci_palette,
             marker="o", ax=axes_ci[2, 1])
axes_ci[2, 1].set_ylim(ci_rt_ylim)
axes_ci[2, 1].set_title("RT across Blocks — Correct vs Incorrect (T1)")
axes_ci[2, 1].set_xlabel("Block")
axes_ci[2, 1].set_ylabel("Mean RT (ms)")
axes_ci[2, 1].set_xticks([1, 2, 3, 4])
axes_ci[2, 1].legend(title="Response")

plt.suptitle(f"T1 Trials — Correct vs Incorrect: Confidence & RT — {title_tag}", y=1.01)
plt.tight_layout()
out = f"../data/results/exploration_T1_correct_vs_incorrect{file_suffix}.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
subprocess.run(["open", out])

# ── fig_t0: T0 — RT + Confidence (2×2) ──────────────────────────────────────
fig_t0, axes_t0 = plt.subplots(2, 2, figsize=(16, 10))

sns.barplot(data=rt_t0_global, x="comparison_pair_tag", y="rt",
            ax=axes_t0[0, 0], color=color_rt, order=T0_ORDER)
axes_t0[0, 0].set_ylim(cat_rt_ylim)
axes_t0[0, 0].set_title("RT by Category (T0)")
axes_t0[0, 0].set_xlabel("")
axes_t0[0, 0].set_ylabel("Mean RT (ms)")

sns.lineplot(data=rt_t0_block, x="block", y="rt",
             hue="comparison_pair_tag", hue_order=T0_ORDER, marker="o", ax=axes_t0[0, 1])
axes_t0[0, 1].set_ylim(cat_rt_ylim)
axes_t0[0, 1].set_title("RT across Blocks (T0)")
axes_t0[0, 1].set_xlabel("Block")
axes_t0[0, 1].set_ylabel("Mean RT (ms)")
axes_t0[0, 1].set_xticks([1, 2, 3, 4])
axes_t0[0, 1].legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)

sns.barplot(data=conf_t0_global, x="comparison_pair_tag", y="confidence_response",
            ax=axes_t0[1, 0], color=color_conf, order=T0_ORDER)
axes_t0[1, 0].set_ylim(cat_conf_ylim)
axes_t0[1, 0].set_title("Confidence by Category (T0)")
axes_t0[1, 0].set_xlabel("Category")
axes_t0[1, 0].set_ylabel("Mean Confidence (0–100)")

sns.lineplot(data=conf_t0_block, x="block", y="confidence_response",
             hue="comparison_pair_tag", hue_order=T0_ORDER, marker="o", ax=axes_t0[1, 1])
axes_t0[1, 1].set_ylim(cat_conf_ylim)
axes_t0[1, 1].set_title("Confidence across Blocks (T0)")
axes_t0[1, 1].set_xlabel("Block")
axes_t0[1, 1].set_ylabel("Mean Confidence (0–100)")
axes_t0[1, 1].set_xticks([1, 2, 3, 4])
axes_t0[1, 1].legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)

plt.suptitle(f"T0 Trials — RT & Confidence by Category — {title_tag}", y=1.01)
plt.tight_layout()
out = f"../data/results/exploration_by_category_T0{file_suffix}.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
subprocess.run(["open", out])

# ── fig_t2: T2 — RT + Confidence (2×2) ──────────────────────────────────────
fig_t2, axes_t2 = plt.subplots(2, 2, figsize=(16, 10))

sns.barplot(data=rt_t2_global, x="comparison_pair_tag", y="rt",
            ax=axes_t2[0, 0], color=color_rt, order=T2_ORDER)
axes_t2[0, 0].set_ylim(cat_rt_ylim)
axes_t2[0, 0].set_title("RT by Category (T2)")
axes_t2[0, 0].set_xlabel("")
axes_t2[0, 0].set_ylabel("Mean RT (ms)")

sns.lineplot(data=rt_t2_block, x="block", y="rt",
             hue="comparison_pair_tag", hue_order=T2_ORDER, marker="o", ax=axes_t2[0, 1])
axes_t2[0, 1].set_ylim(cat_rt_ylim)
axes_t2[0, 1].set_title("RT across Blocks (T2)")
axes_t2[0, 1].set_xlabel("Block")
axes_t2[0, 1].set_ylabel("Mean RT (ms)")
axes_t2[0, 1].set_xticks([1, 2, 3, 4])
axes_t2[0, 1].legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)

sns.barplot(data=conf_t2_global, x="comparison_pair_tag", y="confidence_response",
            ax=axes_t2[1, 0], color=color_conf, order=T2_ORDER)
axes_t2[1, 0].set_ylim(cat_conf_ylim)
axes_t2[1, 0].set_title("Confidence by Category (T2)")
axes_t2[1, 0].set_xlabel("Category")
axes_t2[1, 0].set_ylabel("Mean Confidence (0–100)")

sns.lineplot(data=conf_t2_block, x="block", y="confidence_response",
             hue="comparison_pair_tag", hue_order=T2_ORDER, marker="o", ax=axes_t2[1, 1])
axes_t2[1, 1].set_ylim(cat_conf_ylim)
axes_t2[1, 1].set_title("Confidence across Blocks (T2)")
axes_t2[1, 1].set_xlabel("Block")
axes_t2[1, 1].set_ylabel("Mean Confidence (0–100)")
axes_t2[1, 1].set_xticks([1, 2, 3, 4])
axes_t2[1, 1].legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)

plt.suptitle(f"T2 Trials — RT & Confidence by Category — {title_tag}", y=1.01)
plt.tight_layout()
out = f"../data/results/exploration_by_category_T2{file_suffix}.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
subprocess.run(["open", out])

# ── Transition exposure analysis ──────────────────────────────────────────────
# For each T1 test trial, count how many times the participant saw the specific
# tested transition (base → plausible) in learning phases up to that block.
# trans_raw and tc were computed earlier and are reused here.

# Reuse _t1_early (computed above) — already has trans_plausible and trans_implausible.
# Extend to include timed-out trials for the full T1 set; those rows keep trans = 0.
t1_exp = tt[tt["comparison_type"] == "T1"].copy()
_plaus_left = (
    t1_exp["option_a_plausible"].astype(bool) == t1_exp["left_is_option_a"].astype(bool)
)
t1_exp["plausible_node"]   = t1_exp["option_left"].where(_plaus_left,  t1_exp["option_right"])
t1_exp["implausible_node"] = t1_exp["option_right"].where(_plaus_left, t1_exp["option_left"])
t1_exp = t1_exp.merge(
    tc.rename(columns={"src": "base_node", "dst": "_pn", "n_cumul": "trans_plausible"}),
    left_on=["participant_id", "block", "base_node", "plausible_node"],
    right_on=["participant_id", "block", "base_node", "_pn"], how="left"
).drop(columns="_pn")
t1_exp["trans_plausible"] = t1_exp["trans_plausible"].fillna(0).astype(int)
t1_exp = t1_exp.merge(
    tc.rename(columns={"src": "base_node", "dst": "_in", "n_cumul": "trans_implausible"}),
    left_on=["participant_id", "block", "base_node", "implausible_node"],
    right_on=["participant_id", "block", "base_node", "_in"], how="left"
).drop(columns="_in")
t1_exp["trans_implausible"] = t1_exp["trans_implausible"].fillna(0).astype(int)
t1_exp["trans_diff"] = t1_exp["trans_plausible"] - t1_exp["trans_implausible"]

# Step 5: print summaries
trans_freq = (
    trans_raw.groupby(["participant_id", "src", "dst"])
    .size().reset_index(name="total_seen")
    .sort_values(["participant_id", "src", "dst"])
)
print("\n── TRANSITION FREQUENCIES (learning phase, all blocks) ──")
print(trans_freq.to_string(index=False))

print("\n── TRANSITION EXPOSURE DISTRIBUTION (T1 trials, cumulative) ──")
print(t1_exp[["trans_plausible", "trans_implausible", "trans_diff"]].describe().round(2).to_string())

t1_exp_resp = t1_exp[t1_exp["timed_out"] == False]

trans_acc_p = (
    t1_exp_resp.groupby("trans_plausible")
    .agg(n_trials=("correct", "count"), mean_correct=("correct", "mean"))
    .round(3).reset_index()
)
trans_acc_d = (
    t1_exp_resp.groupby("trans_diff")
    .agg(n_trials=("correct", "count"), mean_correct=("correct", "mean"))
    .round(3).reset_index()
)
print("\n── ACCURACY BY PLAUSIBLE TRANSITION COUNT (T1, cumulative) ──")
print(trans_acc_p.to_string(index=False))
print("\n── ACCURACY BY TRANSITION COUNT DIFFERENCE (plausible − implausible, T1) ──")
print(trans_acc_d.to_string(index=False))

# Step 6: bar charts
acc_by_p = (
    t1_exp_resp.groupby("trans_plausible")["correct"].mean().reset_index()
)
acc_by_d = (
    t1_exp_resp.groupby("trans_diff")["correct"].mean().reset_index()
)

fig_trans, (ax_tp, ax_td) = plt.subplots(1, 2, figsize=(14, 5))

sns.barplot(data=acc_by_p, x="trans_plausible", y="correct", ax=ax_tp, color=color_acc)
ax_tp.axhline(0.5, color="black", linestyle="--", linewidth=0.8)
ax_tp.set_title("Accuracy by Plausible Transition Count (T1)")
ax_tp.set_xlabel("Times base → plausible seen in learning (cumulative)")
ax_tp.set_ylabel("Mean Accuracy")

sns.barplot(data=acc_by_d, x="trans_diff", y="correct", ax=ax_td, color="slateblue")
ax_td.axhline(0.5, color="black", linestyle="--", linewidth=0.8)
ax_td.set_title("Accuracy by Transition Count Difference (T1)")
ax_td.set_xlabel("Count(plausible) − Count(implausible) seen in learning")
ax_td.set_ylabel("Mean Accuracy")

plt.suptitle(f"Transition Exposure vs Accuracy — {title_tag}", y=1.01)
plt.tight_layout()
out = f"../data/results/exploration_transition_exposure{file_suffix}.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
subprocess.run(["open", out])

# ── fig_heatmap: fractal × node assignment counts ────────────────────────────
# Deduplicate to one row per (participant, node) — the fractal is constant
# within a participant, so any trial row will do.
node_order    = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
fractal_order = sorted(tt["base_fractal"].dropna().unique())   # alphabetical → S/A grouped by number

assignment = (
    tt.dropna(subset=["base_fractal"])
    .drop_duplicates(subset=["participant_id", "base_node"])[["base_node", "base_fractal"]]
    .groupby(["base_fractal", "base_node"])
    .size()
    .unstack(fill_value=0)
    .reindex(index=fractal_order, columns=node_order, fill_value=0)
)

fig_hm, ax_hm = plt.subplots(figsize=(9, 6))
sns.heatmap(
    assignment,
    ax=ax_hm,
    annot=True,
    fmt="d",
    cmap="YlOrRd",
    linewidths=0.5,
    linecolor="white",
    cbar_kws={"label": "Number of participants"},
)
ax_hm.set_xlabel("Node position")
ax_hm.set_ylabel("Fractal")
ax_hm.set_title(f"Fractal–Node Assignment Counts — {title_tag}")
plt.tight_layout()
out = f"../data/results/exploration_fractal_node_heatmap{file_suffix}.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
subprocess.run(["open", out])