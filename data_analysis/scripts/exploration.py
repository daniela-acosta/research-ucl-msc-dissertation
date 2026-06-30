import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

ct = pd.read_csv("../data/results/learning_trials.csv")
tt = pd.read_csv("../data/results/test_trials.csv")
print(tt.head())

# GLOBAL
# COVER TASK
ct_res = (
    ct[ct["responded"]]
    .groupby("participant_id")
    .agg(mean_rt=("cover_rt", "mean"), accuracy=("cover_correct", "mean"))
    .reset_index()
)

# 2AFC
tt_res = (
    tt[tt["timed_out"] == False]
    .groupby("participant_id")
    .agg(mean_rt=("rt", "mean"), accuracy=("accuracy", "mean"))
    .reset_index()
)

# CONFIDENCE
conf_res = (
    tt[tt["timed_out"] == False]
    .groupby("participant_id")
    .agg(mean_rt=("confidence_rt", "mean"), mean_conf=("confidence_response", "mean"))
    .reset_index()
)

print("COVER TASK")
print("------------------------")
print(ct_res)
print("------------------------")
print("      ")
print("2AFC")
print("------------------------")
print(tt_res)
print("------------------------")
print("      ")
print("CONFIDENCE")
print("------------------------")
print(conf_res)
print("------------------------")

# BY BLOCK
# COVER TASK
ct_res_block = (
    ct[ct["responded"]]
    .groupby(["participant_id", "block"])
    .agg(mean_rt=("cover_rt", "mean"), accuracy=("cover_correct", "mean"))
    .reset_index()
)

fig1, axes1 = plt.subplots(1, 2, figsize=(12, 5))

sns.lineplot(data=ct_res_block, x="block", y="mean_rt", marker="o", ax=axes1[0])
axes1[0].set_title("Mean RT by Block")
axes1[0].set_xticks([1, 2, 3, 4])
# axes1[0].set_ylim(550, 750) 

sns.lineplot(data=ct_res_block, x="block", y="accuracy", marker="o", ax=axes1[1])
axes1[1].set_title("Accuracy by Block")
axes1[1].set_xticks([1, 2, 3, 4])
# axes1[1].set_ylim(0.4, 0.7)

plt.tight_layout()
plt.show()

# 2AFC & CONFIDENCE
tt_res_block = (
    tt[tt["timed_out"] == False]
    .groupby(["participant_id", "comparison_type", "block"])
    .agg(mean_rt=("rt", "mean"), accuracy=("accuracy", "mean"))
    .reset_index()
)

fig2, axes2 = plt.subplots(1, 2, figsize=(12, 5))

sns.lineplot(data=tt_res_block, x="block", y="mean_rt", units="comparison_type", estimator=None, marker="o", ax=axes2[0])
axes2[0].set_title("Mean RT by Block")
axes2[0].set_xticks([1, 2, 3, 4])
# axes2[0].set_ylim(550, 750) 

sns.lineplot(data=tt_res_block, x="block", y="accuracy", units="comparison_type", estimator=None, marker="o", ax=axes2[1])
axes2[1].set_title("Accuracy by Block")
axes2[1].set_xticks([1, 2, 3, 4])
# axes2[1].set_ylim(0.4, 0.7)

plt.tight_layout()
plt.show()