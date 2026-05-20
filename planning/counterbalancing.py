import pandas as pd

# ─────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────
NB_NODES = ['A', 'C', 'F', 'H']   # Non-boundary nodes
B_NODES  = ['B', 'D', 'E', 'G']   # Boundary nodes

# (category_id, node_type, n_questions_per_node)
# total pool per category = n_questions_per_node × 4 nodes
CATEGORIES = [
    (1, 'NB', 4),   # 16 questions: 1A1..1A4, 1C1..1C4, 1F1..1F4, 1H1..1H4
    (2, 'NB', 2),   #  8 questions: 2A1..2A2, 2C1..2C2, ...
    (3, 'NB', 2),   #  8 questions
    (4, 'B',  2),   #  8 questions
    (5, 'B',  2),   #  8 questions
    (6, 'B',  4),   # 16 questions
    (7, 'B',  1),   #  4 questions: 7B1, 7D1, 7E1, 7G1
    (8, 'B',  2),   #  8 questions
    (9, 'B',  2),   #  8 questions
]
# Total: 16+8+8 + 8+8+16+4+8+8 = 84 ✓

N_GROUPS = 4
N_BLOCKS = 4

# ─────────────────────────────────────────────────────────────────
# COMPUTE WITHIN-TYPE RANK FOR EACH CATEGORY
# This offsets the node rotation so that within any given block,
# NB categories use different NB nodes, and B categories spread
# across B nodes as much as possible (can't be fully unique since
# 6 B-categories > 4 B-nodes).
# ─────────────────────────────────────────────────────────────────
rank = {}
nb_r = b_r = 0
for cat, ntype, _ in CATEGORIES:
    if ntype == 'NB':
        rank[cat] = nb_r; nb_r += 1
    else:
        rank[cat] = b_r;  b_r += 1

# ─────────────────────────────────────────────────────────────────
# ASSIGNMENT FORMULA
#   node_index  = (group + block + rank[category]) % 4
#   question_no = (block  % n_questions_per_node)  + 1
#
# This guarantees:
#   • Each group sees each category × node exactly once (no within-
#     group repetition across blocks)
#   • n_q=4 categories: each question appears exactly 1× total
#   • n_q=2 categories: each question appears exactly 2× total
#   • n_q=1 categories: each question appears exactly 4× total
# ─────────────────────────────────────────────────────────────────
records = []
for g in range(N_GROUPS):
    for b in range(N_BLOCKS):
        for cat, ntype, n_q in CATEGORIES:
            nodes = NB_NODES if ntype == 'NB' else B_NODES
            node  = nodes[(g + b + rank[cat]) % 4]
            q_num = (b % n_q) + 1
            records.append({
                'group'   : g + 1,
                'block'   : b + 1,
                'category': cat,
                'question': f"{cat}{node}{q_num}"
            })

df = pd.DataFrame(records)

# ─────────────────────────────────────────────────────────────────
# VERIFICATION
# ─────────────────────────────────────────────────────────────────
errors = []

# 1. No within-group question repetition
for g, gdf in df.groupby('group'):
    dupes = gdf[gdf.duplicated('question')]
    if not dupes.empty:
        errors.append(f"Group {g} has duplicate questions: {dupes['question'].tolist()}")

# 2. Each question appears the expected number of times overall
#    expected = 4 / n_q  (from: 16 slots per category ÷ 4 nodes ÷ n_q)
counts = df['question'].value_counts()
for cat, ntype, n_q in CATEGORIES:
    nodes    = NB_NODES if ntype == 'NB' else B_NODES
    expected = N_GROUPS * N_BLOCKS // (len(nodes) * n_q)
    for node in nodes:
        for q in range(1, n_q + 1):
            qname  = f"{cat}{node}{q}"
            actual = counts.get(qname, 0)
            if actual != expected:
                errors.append(f"{qname}: expected {expected}×, got {actual}×")

# 3. Within each block, NB categories use distinct NB nodes
for (g, b), bdf in df.groupby(['group', 'block']):
    nb_qs = bdf[bdf['category'].isin([c for c, t, _ in CATEGORIES if t == 'NB'])]['question']
    nb_used = [q[1] for q in nb_qs]   # extract node letter
    if len(nb_used) != len(set(nb_used)):
        errors.append(f"Group {g} Block {b}: NB categories share a node: {nb_used}")

if errors:
    print("VERIFICATION FAILED:")
    for e in errors: print(" •", e)
else:
    print("✓ No within-group question repetition")
    print("✓ All questions appear the expected number of times")
    print("✓ NB categories always use distinct nodes within a block")

# ─────────────────────────────────────────────────────────────────
# SUMMARY STATS
# ─────────────────────────────────────────────────────────────────
print("\n── Question appearances across all groups ──")
app_counts = df['question'].value_counts()
for label, n_q in [(f"n_q={n}", n) for n in [4, 2, 1]]:
    qs = [f"{cat}{node}{q}"
          for cat, _, ncat_q in CATEGORIES if ncat_q == n_q
          for node in (NB_NODES if [t for c,t,nq in CATEGORIES if c==cat][0]=='NB' else B_NODES)
          for q in range(1, n_q + 1)]
    expected = 4 // n_q
    print(f"  {label} categories → {expected}× each (verified for {len(qs)} questions)")

print("\n── Node usage per block (NB categories) ──")
for (g, b), bdf in df.groupby(['group', 'block']):
    nb_nodes = sorted([q[1] for q in bdf[bdf['category'].isin(
        [c for c, t, _ in CATEGORIES if t == 'NB'])]['question']])
    if g == 1:
        print(f"  Group {g}, Block {b}: NB nodes used = {nb_nodes}")

# ─────────────────────────────────────────────────────────────────
# OUTPUT TABLE
# ─────────────────────────────────────────────────────────────────
pivot = (df.sort_values(['block', 'category'])
           .pivot_table(index=['block', 'category'],
                        columns='group',
                        values='question',
                        aggfunc='first'))
pivot.columns = [f'Group_{g}' for g in pivot.columns]
pivot = pivot.reset_index()
pivot.insert(0, 'trial', range(1, len(pivot) + 1))

print("\n── Counterbalancing table (36 trials × 4 groups) ──\n")
# Print with block separators for readability
prev_block = None
for _, row in pivot.iterrows():
    if row['block'] != prev_block:
        if prev_block is not None:
            print()
        print(f"  {'trial':<6} {'block':<6} {'cat':<5} {'Group_1':<10} {'Group_2':<10} {'Group_3':<10} Group_4")
        print("  " + "─"*55)
        prev_block = row['block']
    print(f"  {int(row['trial']):<6} {int(row['block']):<6} {int(row['category']):<5} "
          f"{row['Group_1']:<10} {row['Group_2']:<10} {row['Group_3']:<10} {row['Group_4']}")

# Save to CSV
pivot.to_csv('../data/counterbalancing_table.csv', index=False)
print("\n✓ Table saved to counterbalancing_table.csv")