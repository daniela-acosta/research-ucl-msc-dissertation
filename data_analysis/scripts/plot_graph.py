"""
plot_graph.py
-------------
Draws the community graph structure with the actual fractal images assigned
to each node for a given participant.

Usage (from data_analysis/):
    python scripts/plot_graph.py --participant local_1199466
"""

import argparse
import json
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
import numpy as np

REPO_ROOT    = Path(__file__).resolve().parents[2]
RESULTS_DIR  = REPO_ROOT / "data" / "results"
ASSETS_DIR   = REPO_ROOT / "experiment" / "assets"

# Fixed node positions (in data coordinates, y up)
POS = {
    'A': (1.0, 2.2), 'B': (2.8, 2.2), 'C': (1.0, 0.8), 'D': (2.8, 0.8),
    'E': (4.8, 2.2), 'F': (6.6, 2.2), 'G': (4.8, 0.8), 'H': (6.6, 0.8),
}

INTRA_EDGES = [
    ('A','B'), ('A','C'), ('A','D'), ('B','C'), ('C','D'),
    ('E','F'), ('E','H'), ('F','G'), ('F','H'), ('G','H'),
]
CROSS_EDGES = [('B','E'), ('D','G')]

COMMUNITY_BOUNDS = {
    1: (0.2, 0.1, 3.4, 2.8),   # x, y, width, height
    2: (4.0, 0.1, 3.4, 2.8),
}
COMMUNITY_COLORS = {1: '#f0ecff', 2: '#eaf4ff'}
COMMUNITY_EDGE   = {1: '#c8bfee', 2: '#b0d0e8'}
COMMUNITY_LABELS = {1: (1.9, 3.05, 'Group 1'), 2: (5.7, 3.05, 'Group 2')}


def _get_stimulus_map(participant_id: str) -> dict:
    """Read the stimulus_map from the demographics component for this participant."""
    raw_pid = participant_id.replace("local_", "")
    for study_dir in sorted(RESULTS_DIR.iterdir()):
        if not study_dir.name.startswith("study_result_"):
            continue
        for comp_dir in sorted(study_dir.iterdir()):
            data_file = comp_dir / "data.txt"
            if not data_file.exists():
                continue
            try:
                payload = json.loads(data_file.read_text())
            except Exception:
                continue
            if isinstance(payload, dict) and "stimulus_map" in payload:
                pid = payload.get("prolific_pid", "") or f"local_{study_dir.name.split('_')[-1]}"
                if pid == participant_id or study_dir.name.endswith(raw_pid):
                    return payload["stimulus_map"]
    raise ValueError(f"No stimulus_map found for participant '{participant_id}'")


def plot_graph(participant_id: str) -> None:
    stimulus_map = _get_stimulus_map(participant_id)

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.set_xlim(-0.1, 7.8)
    ax.set_ylim(-0.2, 3.5)
    ax.set_aspect('equal')
    ax.axis('off')

    # Community background boxes
    for comm, (x, y, w, h) in COMMUNITY_BOUNDS.items():
        ax.add_patch(patches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.08",
            facecolor=COMMUNITY_COLORS[comm],
            edgecolor=COMMUNITY_EDGE[comm],
            linewidth=1.5,
            zorder=0,
        ))
        lx, ly, label = COMMUNITY_LABELS[comm]
        ax.text(lx, ly, label, ha='center', va='bottom',
                fontsize=10, color='#888888', fontweight='bold',
                transform=ax.transData)

    # Intra-community edges
    for n1, n2 in INTRA_EDGES:
        x1, y1 = POS[n1]
        x2, y2 = POS[n2]
        ax.plot([x1, x2], [y1, y2], color='#8888aa', linewidth=1.5, zorder=1)

    # Cross-community edges (dashed)
    for n1, n2 in CROSS_EDGES:
        x1, y1 = POS[n1]
        x2, y2 = POS[n2]
        ax.plot([x1, x2], [y1, y2], color='#c07850',
                linewidth=1.5, linestyle='--', dashes=(6, 4), zorder=1)

    # Node images
    for node, (x, y) in POS.items():
        fname = stimulus_map.get(node)
        if fname:
            img_path = ASSETS_DIR / fname
            if img_path.exists():
                img = mpimg.imread(str(img_path))
                imagebox = OffsetImage(img, zoom=0.22, resample=True)
                ab = AnnotationBbox(imagebox, (x, y),
                                    frameon=True,
                                    bboxprops=dict(
                                        boxstyle='circle,pad=0.1',
                                        edgecolor='#555577',
                                        linewidth=1.5,
                                        facecolor='white',
                                    ),
                                    zorder=3)
                ax.add_artist(ab)
        # Node label below image
        ax.text(x, y - 0.35, node, ha='center', va='top',
                fontsize=8, color='#555555', zorder=4)

    # Legend
    ax.plot([], [], color='#8888aa', linewidth=1.5, label='Within-community edge')
    ax.plot([], [], color='#c07850', linewidth=1.5, linestyle='--',
            dashes=(6, 4), label='Cross-community edge')
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.04),
              ncol=2, frameon=False, fontsize=9)

    ax.set_title(f"Graph Structure — {participant_id}", pad=12)

    out = RESULTS_DIR / f"graph_structure_{participant_id}.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved → {out}")
    subprocess.run(["open", str(out)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant", "-p", required=True)
    args = parser.parse_args()
    plot_graph(args.participant)
