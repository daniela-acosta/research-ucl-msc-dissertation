import subprocess

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

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

print("\n── LEARNING (cover task) ──")
print(ct_res.to_string(index=False))

print("\n── TEST (2AFC + confidence) ──")
print(tt_res.to_string(index=False))

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

# ── ylim knobs ───────────────────────────────────────────────────────────────
ct_acc_ylim  = (0.85, 1.0)  # cover task accuracy
tt_acc_ylim  = (0.5,  1.0)  # 2AFC accuracy
tt_conf_ylim = (50,   65)   # mean confidence

# ── colors ──────────────────────────────────────────────────────────────────
color_rt   = "steelblue"
color_acc  = "darkorange"
color_conf = "mediumseagreen"
color_crt  = "mediumpurple"

fig, (ax_ct, ax_2afc, ax_conf) = plt.subplots(1, 3, figsize=(16, 5))

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
ax_conf.set_title("Confidence")
ax_conf.set_xticks([1, 2, 3, 4])
ax_conf.set_xlabel("Block")

plt.suptitle("By Block — Global", y=1.01)
plt.tight_layout()
plt.savefig("../data/results/exploration_by_block.png", dpi=150, bbox_inches="tight")
plt.close()
subprocess.run(["open", "../data/results/exploration_by_block.png"])

# Split by comparison type
t1 = tt[tt["comparison_type"] == "T1"].copy()
t0 = tt[tt["comparison_type"] == "T0"].copy()
t2 = tt[tt["comparison_type"] == "T2"].copy()

t1_resp = t1[t1["timed_out"] == False]
t0_resp = t0[t0["timed_out"] == False]
t2_resp = t2[t2["timed_out"] == False]

cat_acc_ylim  = (0.0, 1.1)
cat_rt_ylim   = (1200, 2500)
cat_conf_ylim = (30, 90)

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

plt.suptitle("T1 Trials — Accuracy, RT & Confidence by Category", y=1.01)
plt.tight_layout()
plt.savefig("../data/results/exploration_by_category_T1.png", dpi=150, bbox_inches="tight")
plt.close()
subprocess.run(["open", "../data/results/exploration_by_category_T1.png"])

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

plt.suptitle("T0 Trials — RT & Confidence by Category", y=1.01)
plt.tight_layout()
plt.savefig("../data/results/exploration_by_category_T0.png", dpi=150, bbox_inches="tight")
plt.close()
subprocess.run(["open", "../data/results/exploration_by_category_T0.png"])

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

plt.suptitle("T2 Trials — RT & Confidence by Category", y=1.01)
plt.tight_layout()
plt.savefig("../data/results/exploration_by_category_T2.png", dpi=150, bbox_inches="tight")
plt.close()
subprocess.run(["open", "../data/results/exploration_by_category_T2.png"])