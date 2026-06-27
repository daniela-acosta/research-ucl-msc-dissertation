"""
Random walk coverage analysis for the graph learning experiment.

Simulates random walks over the 8-node community-structured graph and reports
how well nodes are covered at different walk lengths. Use this to inform the
choice of walkLength before deployment.

Key question: what proportion of walks miss at least one node entirely?
Since the test phase asks about ALL nodes, participants need some exposure to
every node during learning. This script helps find a walk length where coverage
is acceptable.

Usage:
    python simulate_walk_coverage.py
"""

import random
import statistics
from collections import Counter

# ── Graph definition ────────────────────────────────────────────────────────
ADJACENCY = {
    'A': ['B', 'C', 'D'],
    'B': ['A', 'C', 'E'],
    'C': ['A', 'B', 'D'],
    'D': ['A', 'C', 'G'],
    'E': ['B', 'F', 'H'],
    'F': ['E', 'G', 'H'],
    'G': ['D', 'F', 'H'],
    'H': ['E', 'F', 'G'],
}
NODES      = list(ADJACENCY.keys())
COMMUNITY  = {n: 1 for n in 'ABCD'} | {n: 2 for n in 'EFGH'}

# ── Simulation parameters ───────────────────────────────────────────────────
N_SIMS        = 100_000          # number of walks to simulate per length
WALK_LENGTHS  = [24, 26, 40, 56, 80]   # lengths to compare
DETAIL_LENGTH = 24               # length for per-node breakdown


def simulate_walk(length):
    """Return a Counter of node visits for a single random walk of given length."""
    current = random.choice(NODES)
    counts  = Counter([current])
    for _ in range(length - 1):
        current = random.choice(ADJACENCY[current])
        counts[current] += 1
    return counts


# ── Per-node detail at DETAIL_LENGTH ────────────────────────────────────────
print(f"=== Per-node breakdown  (walk length {DETAIL_LENGTH}, {N_SIMS:,} simulations) ===\n")

missed_any   = 0
min_visits   = Counter()
node_visits  = {n: [] for n in NODES}
cross_counts = []

for _ in range(N_SIMS):
    current = random.choice(NODES)
    walk    = [current]
    for _ in range(DETAIL_LENGTH - 1):
        current = random.choice(ADJACENCY[current])
        walk.append(current)

    counts = Counter(walk)
    mn = min(counts[n] for n in NODES)
    if mn == 0:
        missed_any += 1
    min_visits[mn] += 1
    for n in NODES:
        node_visits[n].append(counts[n])
    crosses = sum(
        1 for i in range(len(walk) - 1)
        if COMMUNITY[walk[i]] != COMMUNITY[walk[i + 1]]
    )
    cross_counts.append(crosses)

print(f"Walks where ≥1 node never appears:  {missed_any:,} ({100*missed_any/N_SIMS:.1f}%)\n")

print("Distribution of minimum node visits per walk:")
for k in sorted(min_visits):
    print(f"  min = {k}×: {100*min_visits[k]/N_SIMS:.1f}%")

print("\nPer-node appearance statistics:")
print(f"  {'Node':<6} {'Type':<5} {'Mean':>6} {'Std':>6} {'Never seen':>12}")
NB_NODES = {'A', 'C', 'F', 'H'}
for n in NODES:
    v    = node_visits[n]
    mean = statistics.mean(v)
    std  = statistics.stdev(v)
    zero = sum(1 for x in v if x == 0)
    ntype = 'NB' if n in NB_NODES else 'B'
    print(f"  {n:<6} {ntype:<5} {mean:>6.2f} {std:>6.2f} {zero:>7,} ({100*zero/N_SIMS:.1f}%)")

# Visit count distribution per node — shows clustering effect.
# High variance (std ≈ 2) comes from the walk getting stuck in one community:
# when it stays in community 1, nodes in community 2 accumulate 0s, and vice versa.
MAX_SHOWN = 10
print(f"\nVisit count distribution per node (% of {N_SIMS:,} walks):")
header = f"  {'Node':<6} {'Type':<5}" + "".join(f"  {k}×" for k in range(MAX_SHOWN + 1)) + "  ≥11×"
print(header)
print("  " + "─" * (len(header) - 2))
for n in NODES:
    v     = node_visits[n]
    ntype = 'NB' if n in NB_NODES else 'B'
    row   = f"  {n:<6} {ntype:<5}"
    for k in range(MAX_SHOWN + 1):
        pct = 100 * sum(1 for x in v if x == k) / N_SIMS
        row += f"  {pct:3.0f}"
    pct_high = 100 * sum(1 for x in v if x > MAX_SHOWN) / N_SIMS
    row += f"  {pct_high:3.0f}"
    print(row)
print(f"  {'':6} {'':5}" + "".join(f"  {k:>3}" for k in range(MAX_SHOWN + 1)) + "   >10  ← visits")

print(
    f"\nCommunity crossings per walk:  "
    f"mean={statistics.mean(cross_counts):.2f}  "
    f"std={statistics.stdev(cross_counts):.2f}  "
    f"min={min(cross_counts)}  max={max(cross_counts)}"
)

# ── Cross-length comparison ──────────────────────────────────────────────────
print(f"\n\n=== Coverage comparison across walk lengths ({N_SIMS:,} simulations each) ===\n")
print(f"  {'Length':>8}  {'Miss ≥1 node':>14}  {'All nodes ≥2×':>15}  {'Expected/node':>14}")
print("  " + "─" * 58)

for length in WALK_LENGTHS:
    missed = 0
    min2   = 0
    for _ in range(N_SIMS):
        counts = simulate_walk(length)
        mn = min(counts[n] for n in NODES)
        if mn == 0:
            missed += 1
        if mn >= 2:
            min2 += 1
    print(
        f"  {length:>8}  "
        f"{100*missed/N_SIMS:>13.1f}%  "
        f"{100*min2/N_SIMS:>14.1f}%  "
        f"{length/8:>14.1f}"
    )
