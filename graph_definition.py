from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import networkx as nx


# ---------- 1) Define your graph + communities ----------

# Example node labels; replace with your own if needed
NODES = list("ABCDEFGH")

# Community assignment: change as needed
COMMUNITY: Dict[str, int] = {
    "A": 0, "B": 0, "C": 0, "D": 0,
    "E": 1, "F": 1, "G": 1, "H": 1,
}

# Define edges (undirected)
EDGES: List[Tuple[str, str]] = [
    # Community 0 edges
    ("A", "B"), ("A", "C"), ("A", "D"), ("B", "C"), ("C", "D"),
    # Community 1 edges
    ("E", "F"), ("E", "H"), ("F", "G"), ("F", "H"), ("H", "G"),
    # Cross-community edges (example)
    ("B", "E"), ("D", "G"),
]

G = nx.Graph()
G.add_nodes_from(NODES)
G.add_edges_from(EDGES)


# ---------- 2) Helper functions for criteria ----------

def is_boundary_node(G: nx.Graph, node: str, community: Dict[str, int]) -> bool:
    """Boundary = has at least one edge to a node in the other community."""
    node_comm = community[node]
    for nbr in G.neighbors(node):
        if community[nbr] != node_comm:
            return True
    return False


def shortest_steps(G: nx.Graph, src: str, dst: str) -> float:
    """Shortest path length in number of edges. Returns NaN if unreachable."""
    if src == dst:
        return 0.0
    try:
        return float(nx.shortest_path_length(G, source=src, target=dst))
    except nx.NetworkXNoPath:
        return np.nan


# ---------- 3) Build transition table (base -> destination) ----------

rows = []
boundary_cache = {n: is_boundary_node(G, n, COMMUNITY) for n in G.nodes}

for base in G.nodes:
    for dest in G.nodes:
        if dest == base:
            continue

        plausible = G.has_edge(base, dest)  # connected by an edge
        steps = shortest_steps(G, base, dest)
        rows.append({
            "base": base,
            "dest": dest,
            "plausible": plausible,
            "base_is_boundary": boundary_cache[base],
            "steps": steps,
            "base_community": COMMUNITY[base],
            "dest_community": COMMUNITY[dest],
        })

transitions_df = pd.DataFrame(rows)

# Save transitions table
transitions_df.to_csv("transition_criteria.csv", index=False)


# ---------- 4) Build all 2AFC question candidates ----------

def classify_T(p1: bool, p2: bool) -> str:
    """The T0/T1/T2 definition based on plausibility of the two compared transitions."""
    if (not p1) and (not p2):
        return "T0" # none plausible
    if p1 != p2:
        return "T1" # one plausible
    return "T2"  # both plausible


q_rows = []
# For each base, choose unordered pairs of destinations
for base in G.nodes:
    dests = [d for d in G.nodes if d != base]
    for d1, d2 in itertools.combinations(dests, 2):
        p1 = G.has_edge(base, d1)
        p2 = G.has_edge(base, d2)

        q_rows.append({
            "base": base,

            "optionA_dest": d1,
            "optionA_plausible": p1,
            "optionA_steps": shortest_steps(G, base, d1),
            "optionA_dest_community": COMMUNITY[d1],

            "optionB_dest": d2,
            "optionB_plausible": p2,
            "optionB_steps": shortest_steps(G, base, d2),
            "optionB_dest_community": COMMUNITY[d2],

            "base_is_boundary": boundary_cache[base],
            "base_community": COMMUNITY[base],

            "comparison_type": classify_T(p1, p2),
        })

questions_df = pd.DataFrame(q_rows)
questions_df.to_csv("2afc_question_candidates.csv", index=False)

print("Wrote: transition_criteria.csv and 2afc_question_candidates.csv")