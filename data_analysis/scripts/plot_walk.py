"""
plot_walk.py
------------
One-off visualisation of the random walk sequence for a single participant.
Shows node visited at each step, coloured by community, across all 4 blocks.

Usage (from data_analysis/):
    python scripts/plot_walk.py --participant local_1199466
"""

import argparse
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

REPO_ROOT    = Path(__file__).resolve().parents[2]
LEARNING_CSV = REPO_ROOT / "data" / "results" / "learning_trials.csv"
OUT_DIR      = REPO_ROOT / "data" / "results"

# Node y-positions: community 1 (top) then community 2 (bottom), NB before B within each
NODE_ORDER   = ['A', 'C', 'B', 'D', 'E', 'H', 'F', 'G']
NODE_Y       = {n: i for i, n in enumerate(NODE_ORDER)}

COMMUNITY    = {n: 1 for n in ['A', 'B', 'C', 'D']}
COMMUNITY.update({n: 2 for n in ['E', 'F', 'G', 'H']})
BOUNDARY     = {'B', 'D', 'E', 'G'}

COLOR_C1     = '#5B7FBF'   # community 1 — blue
COLOR_C2     = '#E07B54'   # community 2 — orange


def plot_walk(participant_id: str) -> None:
    lt = pd.read_csv(LEARNING_CSV)
    data = lt[lt["participant_id"] == participant_id].copy()

    if data.empty:
        raise ValueError(
            f"Participant '{participant_id}' not found. "
            f"Available: {sorted(lt['participant_id'].unique())}"
        )

    blocks = sorted(data["block"].unique())
    fig, axes = plt.subplots(1, len(blocks), figsize=(5 * len(blocks), 4),
                             sharey=True)
    if len(blocks) == 1:
        axes = [axes]

    for ax, block in zip(axes, blocks):
        bd = data[data["block"] == block].sort_values("step")
        steps = bd["step"].values
        nodes = bd["node"].values
        ys    = [NODE_Y[n] for n in nodes]
        colors = [COLOR_C1 if COMMUNITY[n] == 1 else COLOR_C2 for n in nodes]

        # Line connecting steps
        ax.plot(steps, ys, color='#cccccc', linewidth=0.8, zorder=1)

        # Scatter: filled circle = NB, ring = boundary
        for step, y, node, c in zip(steps, ys, nodes, colors):
            if node in BOUNDARY:
                ax.scatter(step, y, color=c, s=60, zorder=3,
                           facecolors='white', edgecolors=c, linewidths=1.8)
            else:
                ax.scatter(step, y, color=c, s=60, zorder=3)

        # Dashed line between communities
        ax.axhline(3.5, color='#aaaaaa', linestyle='--', linewidth=0.8)

        ax.set_title(f"Block {block}")
        ax.set_xlabel("Step")
        ax.set_yticks(list(NODE_Y.values()))
        ax.set_yticklabels(NODE_ORDER)
        ax.invert_yaxis()
        ax.set_xlim(steps[0] - 0.5, steps[-1] + 0.5)

    axes[0].set_ylabel("Node")

    # Legend
    legend_handles = [
        mpatches.Patch(color=COLOR_C1, label='Community 1'),
        mpatches.Patch(color=COLOR_C2, label='Community 2'),
        plt.scatter([], [], s=60, facecolors='white', edgecolors='grey',
                    linewidths=1.8, label='Boundary node'),
        plt.scatter([], [], s=60, color='grey', label='Non-boundary node'),
    ]
    fig.legend(handles=legend_handles, loc='lower center', ncol=4,
               bbox_to_anchor=(0.5, -0.08), frameon=False)

    fig.suptitle(f"Random Walk Sequence — {participant_id}", y=1.02)
    plt.tight_layout()

    out = OUT_DIR / f"walk_sequence_{participant_id}.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved → {out}")
    subprocess.run(["open", str(out)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant", "-p", required=True,
                        help="participant_id to plot")
    args = parser.parse_args()
    plot_walk(args.participant)
