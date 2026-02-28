from __future__ import annotations

import itertools
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import networkx as nx


# ---------- 1) Define graph + communities ----------

NODES = list("ABCDEFGH")

COMMUNITY: Dict[str, int] = {
    "A": 0, "B": 0, "C": 0, "D": 0,
    "E": 1, "F": 1, "G": 1, "H": 1,
}

EDGES: List[Tuple[str, str]] = [
    # Community 0 edges
    ("A", "B"), ("A", "C"), ("A", "D"), ("B", "C"), ("C", "D"),
    # Community 1 edges
    ("E", "F"), ("E", "H"), ("F", "G"), ("F", "H"), ("H", "G"),
    # Cross-community edges
    ("B", "E"), ("D", "G"),
]

G = nx.Graph()
G.add_nodes_from(NODES)
G.add_edges_from(EDGES)


# ---------- 2) Helpers ----------

def is_boundary_node(G: nx.Graph, node: str, community: Dict[str, int]) -> bool:
    """Boundary = has at least one edge to a node in the other community."""
    node_comm = community[node]
    return any(community[nbr] != node_comm for nbr in G.neighbors(node))


def shortest_steps(G: nx.Graph, src: str, dst: str) -> float:
    """Shortest path length in number of edges. Returns NaN if unreachable."""
    if src == dst:
        return 0.0
    try:
        return float(nx.shortest_path_length(G, source=src, target=dst))
    except nx.NetworkXNoPath:
        return np.nan


def within_code(base: str, dest: str, community: Dict[str, int]) -> str:
    """W if within-community, X if cross-community."""
    return "W" if community[base] == community[dest] else "X"


def transition_tag(
    plausible: bool,
    base_is_boundary: bool,
    steps: float,
    max_steps_label: int = 3
) -> str:
    """
    Tag format: P/I + B/NB + distance(1..3)
    Example: PB1, INB2
    """
    p = "P" if plausible else "I"
    b = "B" if base_is_boundary else "NB"

    if np.isnan(steps):
        d = "NA"
    else:
        steps_int = int(steps)
        d = str(steps_int) if steps_int <= max_steps_label else f"{max_steps_label}+"

    return f"{p}{b}{d}"


def transition_tag_wx(
    plausible: bool,
    base_is_boundary: bool,
    steps: float,
    wx: str,
    max_steps_label: int = 3
) -> str:
    """
    Tag format: (P/I + B/NB + distance) + W/X
    Example: PB1W, INB2X
    """
    return f"{transition_tag(plausible, base_is_boundary, steps, max_steps_label)}{wx}"


def classify_T(p1: bool, p2: bool) -> str:
    """T0/T1/T2 based on plausibility of the two compared transitions."""
    if (not p1) and (not p2):
        return "T0"
    if p1 != p2:
        return "T1"
    return "T2"


def unordered_pair_tag(tag_a: str, tag_b: str, sep: str = "__") -> str:
    """Order-invariant pairing so (A,B) and (B,A) map to the same label."""
    x, y = sorted([tag_a, tag_b])
    return f"{x}{sep}{y}"


# ---------- 3) Transition-level table (base -> dest) ----------

base_boundary = {n: is_boundary_node(G, n, COMMUNITY) for n in G.nodes}
dest_boundary = base_boundary  # boundary-ness is a node property

rows = []
for base in G.nodes:
    for dest in G.nodes:
        if dest == base:
            continue

        plausible = G.has_edge(base, dest)
        steps = shortest_steps(G, base, dest)

        wx = within_code(base, dest, COMMUNITY)
        same_comm = (wx == "W")

        tag_old = transition_tag(plausible, base_boundary[base], steps, max_steps_label=3)  # PB1
        tag_new = transition_tag_wx(plausible, base_boundary[base], steps, wx, max_steps_label=3)  # PB1W

        rows.append({
            "base": base,
            "dest": dest,

            "plausible": plausible,
            "steps": steps,

            "base_is_boundary": base_boundary[base],
            "dest_is_boundary": dest_boundary[dest],

            "same_community": same_comm,
            "within_code": wx,  # W or X

            "transition_tag": tag_old,        # e.g., PB1
            "transition_tag_wx": tag_new,     # e.g., PB1W

            "base_community": COMMUNITY[base],
            "dest_community": COMMUNITY[dest],
        })

transitions_df = pd.DataFrame(rows)
transitions_df.to_csv("transition_criteria.csv", index=False)


# ---------- 4) 2AFC question candidates (base with two destinations) ----------

q_rows = []
for base in G.nodes:
    dests = [d for d in G.nodes if d != base]
    for d1, d2 in itertools.combinations(dests, 2):
        p1 = G.has_edge(base, d1)
        p2 = G.has_edge(base, d2)

        s1 = shortest_steps(G, base, d1)
        s2 = shortest_steps(G, base, d2)

        wx1 = within_code(base, d1, COMMUNITY)
        wx2 = within_code(base, d2, COMMUNITY)

        # Keep BOTH tags per option
        tA_old = transition_tag(p1, base_boundary[base], s1, max_steps_label=3)         # PB1
        tA_new = transition_tag_wx(p1, base_boundary[base], s1, wx1, max_steps_label=3) # PB1W

        tB_old = transition_tag(p2, base_boundary[base], s2, max_steps_label=3)         # INB2
        tB_new = transition_tag_wx(p2, base_boundary[base], s2, wx2, max_steps_label=3) # INB2X

        comp_T = classify_T(p1, p2)  # T0/T1/T2 based on plausibility

        # Pair tags (order-invariant) for each tagging scheme
        comp_pair_old = unordered_pair_tag(tA_old, tB_old)  # e.g., INB2__PB1
        comp_pair_new = unordered_pair_tag(tA_new, tB_new)  # e.g., INB2X__PB1W

        q_rows.append({
            "base": base,
            "base_is_boundary": base_boundary[base],
            "base_community": COMMUNITY[base],

            "optionA_dest": d1,
            "optionA_plausible": p1,
            "optionA_steps": s1,
            "optionA_within_code": wx1,
            "optionA_same_community": (wx1 == "W"),
            "optionA_dest_is_boundary": dest_boundary[d1],
            "optionA_tag": tA_old,         # PB1
            "optionA_tag_wx": tA_new,      # PB1W

            "optionB_dest": d2,
            "optionB_plausible": p2,
            "optionB_steps": s2,
            "optionB_within_code": wx2,
            "optionB_same_community": (wx2 == "W"),
            "optionB_dest_is_boundary": dest_boundary[d2],
            "optionB_tag": tB_old,         # INB2
            "optionB_tag_wx": tB_new,      # INB2X

            "comparison_type": comp_T,          # T0/T1/T2
            "comparison_pair_tag": comp_pair_old,    # old pair tag (no W/X)
            "comparison_pair_tag_wx": comp_pair_new, # new pair tag (with W/X)
        })

questions_df = pd.DataFrame(q_rows)
questions_df.to_csv("2afc_question_candidates.csv", index=False)

print("Wrote: transition_criteria.csv and 2afc_question_candidates.csv")