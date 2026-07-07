import argparse
import subprocess

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

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
        accuracy_t1=("accuracy", "mean"),          # NaN for T0/T2, so mean is T1-only
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

# BY QUESTION TYPE (averaged across all participants and blocks)
qtype_res = (
    tt[tt["timed_out"] == False]
    .groupby(["comparison_type", "category", "comparison_pair_tag"])
    .agg(
        accuracy        =("accuracy",            "mean"),  # NaN for T0/T2
        mean_rt         =("rt",                  "mean"),
        mean_confidence =("confidence_response", "mean"),
    )
    .round(3)
    .reset_index()
    .sort_values("category")
    .rename(columns={"comparison_pair_tag": "pair_tag", "comparison_type": "type",
                     "mean_rt": "rt", "mean_confidence": "confidence"})
)
print("\n── BY QUESTION TYPE (all participants, all blocks) ──")
print(qtype_res.to_string(index=False))

type_res = (
    tt[tt["timed_out"] == False]
    .groupby("comparison_type")
    .agg(
        accuracy        =("accuracy",            "mean"),
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
        accuracy        =("accuracy",            "mean"),
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
        accuracy        =("accuracy",            "mean"),
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
        accuracy        =("accuracy",            "mean"),
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
        accuracy       =("accuracy",            "mean"),   # NaN for T0/T2, so mean is T1-only
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
tt_acc_ylim  = ylim(tt_res_block["accuracy"])
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
sns.lineplot(data=tt_res_block, x="block", y="accuracy", marker="o", ax=ax_2afc2, color=color_acc)
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
    t1.groupby(["category", "comparison_pair_tag"])["accuracy"]
    .mean().reset_index().sort_values("category")
)
acc_by_cat_block = t1.groupby(["comparison_pair_tag", "block"])["accuracy"].mean().reset_index()
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
_acc_lo, _acc_hi = ylim(acc_by_cat["accuracy"], acc_by_cat_block["accuracy"])
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

sns.barplot(data=acc_by_cat, x="comparison_pair_tag", y="accuracy",
            ax=axes_t1[0, 0], color=color_acc, order=T1_ORDER)
axes_t1[0, 0].axhline(0.5, color="black", linestyle="--", linewidth=0.8)
axes_t1[0, 0].set_ylim(cat_acc_ylim)
axes_t1[0, 0].set_title("Accuracy by Category (T1)")
axes_t1[0, 0].set_xlabel("")
axes_t1[0, 0].set_ylabel("Accuracy")
axes_t1[0, 0].tick_params(axis="x", rotation=30)

sns.lineplot(data=acc_by_cat_block, x="block", y="accuracy",
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
t1_resp_ci["correct"] = t1_resp_ci["accuracy"].map({1.0: "Correct", 0.0: "Incorrect"})

ci_conf_cat   = (t1_resp_ci.groupby(["correct", "comparison_pair_tag"])
                 ["confidence_response"].mean().reset_index())
ci_conf_block = (t1_resp_ci.groupby(["correct", "block"])
                 ["confidence_response"].mean().reset_index())
ci_rt_cat     = (t1_resp_ci.groupby(["correct", "comparison_pair_tag"])
                 ["rt"].mean().reset_index())
ci_rt_block   = (t1_resp_ci.groupby(["correct", "block"])
                 ["rt"].mean().reset_index())

ci_palette  = {"Correct": "seagreen", "Incorrect": "salmon"}
ci_hue_order = ["Correct", "Incorrect"]

ci_conf_ylim = ylim(ci_conf_cat["confidence_response"], ci_conf_block["confidence_response"])
ci_rt_ylim   = ylim(ci_rt_cat["rt"], ci_rt_block["rt"])

fig_ci, axes_ci = plt.subplots(3, 2, figsize=(16, 14))

# Row 1 — overall accuracy (context; same as T1 category figure)
sns.barplot(data=acc_by_cat, x="comparison_pair_tag", y="accuracy",
            ax=axes_ci[0, 0], color=color_acc, order=T1_ORDER)
axes_ci[0, 0].axhline(0.5, color="black", linestyle="--", linewidth=0.8)
axes_ci[0, 0].set_ylim(cat_acc_ylim)
axes_ci[0, 0].set_title("Accuracy by Category (T1)")
axes_ci[0, 0].set_xlabel("")
axes_ci[0, 0].set_ylabel("Accuracy")
axes_ci[0, 0].tick_params(axis="x", rotation=30)

sns.lineplot(data=acc_by_cat_block, x="block", y="accuracy",
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
            hue="correct", hue_order=ci_hue_order, palette=ci_palette,
            ax=axes_ci[1, 0], order=T1_ORDER)
axes_ci[1, 0].set_ylim(ci_conf_ylim)
axes_ci[1, 0].set_title("Confidence by Category — Correct vs Incorrect (T1)")
axes_ci[1, 0].set_xlabel("")
axes_ci[1, 0].set_ylabel("Mean Confidence (0–100)")
axes_ci[1, 0].tick_params(axis="x", rotation=30)
axes_ci[1, 0].legend(title="Response")

sns.lineplot(data=ci_conf_block, x="block", y="confidence_response",
             hue="correct", hue_order=ci_hue_order, palette=ci_palette,
             marker="o", ax=axes_ci[1, 1])
axes_ci[1, 1].set_ylim(ci_conf_ylim)
axes_ci[1, 1].set_title("Confidence across Blocks — Correct vs Incorrect (T1)")
axes_ci[1, 1].set_xlabel("Block")
axes_ci[1, 1].set_ylabel("Mean Confidence (0–100)")
axes_ci[1, 1].set_xticks([1, 2, 3, 4])
axes_ci[1, 1].legend(title="Response")

# Row 3 — RT by correct / incorrect
sns.barplot(data=ci_rt_cat, x="comparison_pair_tag", y="rt",
            hue="correct", hue_order=ci_hue_order, palette=ci_palette,
            ax=axes_ci[2, 0], order=T1_ORDER)
axes_ci[2, 0].set_ylim(ci_rt_ylim)
axes_ci[2, 0].set_title("RT by Category — Correct vs Incorrect (T1)")
axes_ci[2, 0].set_xlabel("Category")
axes_ci[2, 0].set_ylabel("Mean RT (ms)")
axes_ci[2, 0].tick_params(axis="x", rotation=30)
axes_ci[2, 0].legend(title="Response")

sns.lineplot(data=ci_rt_block, x="block", y="rt",
             hue="correct", hue_order=ci_hue_order, palette=ci_palette,
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