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


def transition_tag(
    plausible: bool,
    base_is_boundary: bool,
    steps: float,
    max_steps_label: int = 3
) -> str:
    """
    Tag format: P/I + B/NB + distance(1..3)
    If steps > max_steps_label (or NaN), label as '3+' or 'NA' (edit if you prefer).
    """
    p = "P" if plausible else "I"
    b = "B" if base_is_boundary else "NB"

    if np.isnan(steps):
        d = "NA"
    else:
        steps_int = int(steps)
        d = str(steps_int) if steps_int <= max_steps_label else f"{max_steps_label}+"

    return f"{p}{b}{d}"


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

boundary_cache = {n: is_boundary_node(G, n, COMMUNITY) for n in G.nodes}

rows = []
for base in G.nodes:
    for dest in G.nodes:
        if dest == base:
            continue

        plausible = G.has_edge(base, dest)
        steps = shortest_steps(G, base, dest)
        tag = transition_tag(plausible, boundary_cache[base], steps, max_steps_label=3)

        rows.append({
            "base": base,
            "dest": dest,
            "plausible": plausible,
            "base_is_boundary": boundary_cache[base],
            "steps": steps,
            "transition_tag": tag,
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

        tA = transition_tag(p1, boundary_cache[base], s1, max_steps_label=3)
        tB = transition_tag(p2, boundary_cache[base], s2, max_steps_label=3)

        comp_T = classify_T(p1, p2)                    # keep your old one
        comp_pair = unordered_pair_tag(tA, tB)         # NEW: pair of tags, order-invariant

        q_rows.append({
            "base": base,
            "base_is_boundary": boundary_cache[base],
            "base_community": COMMUNITY[base],

            "optionA_dest": d1,
            "optionA_plausible": p1,
            "optionA_steps": s1,
            "optionA_tag": tA, 

            "optionB_dest": d2,
            "optionB_plausible": p2,
            "optionB_steps": s2,
            "optionB_tag": tB, 

            "comparison_type": comp_T,         
            "comparison_pair_tag": comp_pair,
        })

questions_df = pd.DataFrame(q_rows)
questions_df.to_csv("2afc_question_candidates.csv", index=False)

print("Wrote: transition_criteria.csv and 2afc_question_candidates.csv")