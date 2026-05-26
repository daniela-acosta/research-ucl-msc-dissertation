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


def node_type(is_boundary: bool) -> str:
    """Encode node type as B / NB."""
    return "B" if is_boundary else "NB"


def dist_code(steps: float, max_steps_label: int = 3) -> str:
    """
    Encode shortest-path distance.
    - 1/2/3 for steps <= 3
    - '3+' if > 3
    - 'NA' if unreachable
    """
    if np.isnan(steps):
        return "NA"
    s = int(steps)
    return str(s) if s <= max_steps_label else f"{max_steps_label}+"


def transition_tag_4vars(
    base_is_boundary: bool,
    steps: float,
    wx: str,
    dest_is_boundary: bool,
    max_steps_label: int = 3
) -> str:
    """
    Tag format: {baseType}{dist}{W/X}{destType}
    Example: B1WNB, NB2XB, B3XNB
    """
    bt = node_type(base_is_boundary)
    dt = node_type(dest_is_boundary)
    dc = dist_code(steps, max_steps_label=max_steps_label)
    return f"{bt}{dc}{wx}{dt}"


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


# ---------- 3) Precompute node properties ----------

boundary = {n: is_boundary_node(G, n, COMMUNITY) for n in G.nodes}


# ---------- 4) Transition-level table (base -> dest) ----------

transition_rows = []
for base in G.nodes:
    for dest in G.nodes:
        if dest == base:
            continue

        steps = shortest_steps(G, base, dest)
        wx = within_code(base, dest, COMMUNITY)
        plausible = G.has_edge(base, dest)  # still useful to keep as a column

        tag = transition_tag_4vars(
            base_is_boundary=boundary[base],
            steps=steps,
            wx=wx,
            dest_is_boundary=boundary[dest],
            max_steps_label=3,
        )

        transition_rows.append({
            "base": base,
            "dest": dest,

            "plausible": plausible,
            "steps": steps,

            "base_is_boundary": boundary[base],
            "dest_is_boundary": boundary[dest],

            "within_code": wx,  # W/X relative to base
            "same_community": (wx == "W"),

            "transition_tag": tag,

            "base_community": COMMUNITY[base],
            "dest_community": COMMUNITY[dest],
        })

transitions_df = pd.DataFrame(transition_rows)
transitions_df.to_csv("../data/transition_criteria_v2.csv", index=False)


# ---------- 5) 2AFC question candidates (base with two destinations) ----------

q_rows = []
for base in G.nodes:
    dests = [d for d in G.nodes if d != base]
    for d1, d2 in itertools.combinations(dests, 2):
        # option A stats
        p1 = G.has_edge(base, d1)
        s1 = shortest_steps(G, base, d1)
        wx1 = within_code(base, d1, COMMUNITY)
        tagA = transition_tag_4vars(boundary[base], s1, wx1, boundary[d1], max_steps_label=3)

        # option B stats
        p2 = G.has_edge(base, d2)
        s2 = shortest_steps(G, base, d2)
        wx2 = within_code(base, d2, COMMUNITY)
        tagB = transition_tag_4vars(boundary[base], s2, wx2, boundary[d2], max_steps_label=3)

        # comparison labels
        comp_T = classify_T(p1, p2)  
        comp_pair = unordered_pair_tag(tagA, tagB)

        q_rows.append({
            "base": base,
            "base_is_boundary": boundary[base],
            "base_community": COMMUNITY[base],

            "optionA_dest": d1,
            "optionA_plausible": p1,
            "optionA_steps": s1,
            "optionA_within_code": wx1,
            "optionA_same_community": (wx1 == "W"),
            "optionA_dest_is_boundary": boundary[d1],
            "optionA_tag": tagA,

            "optionB_dest": d2,
            "optionB_plausible": p2,
            "optionB_steps": s2,
            "optionB_within_code": wx2,
            "optionB_same_community": (wx2 == "W"),
            "optionB_dest_is_boundary": boundary[d2],
            "optionB_tag": tagB,

            "comparison_type": comp_T,
            "comparison_pair_tag": comp_pair,
        })

questions_df = pd.DataFrame(q_rows)

# Assign question_number: sequential index (1-based) within each (base, comparison_pair_tag) group.
# Order is determined by itertools.combinations above, which is stable and deterministic.
questions_df["question_number"] = (
    questions_df
    .groupby(["base", "comparison_pair_tag"], sort=False)
    .cumcount() + 1
)

questions_df.to_csv("../data/2afc_question_candidates_v3.csv", index=False)

print("Wrote: transition_criteria_v2.csv and 2afc_question_candidates_v3.csv")