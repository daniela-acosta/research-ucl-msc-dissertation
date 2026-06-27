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
# Total unique questions: 16+8+8 + 8+8+16+4+8+8 = 84 ✓

N_BLOCKS = 4

# ─────────────────────────────────────────────────────────────────
# ASSIGNMENT RULES (no counterbalancing groups)
#
# Every block shows all 4 base nodes for every category (36 questions/block).
# The variant (question number) assigned per (block, category, node) is:
#
#   n/node = 4 (pool-16): variant = block number (1→v1, 2→v2, 3→v3, 4→v4)
#             → each of 16 questions appears exactly once across the experiment
#
#   n/node = 2 (pool-8):  variant = (block − 1) % 2 + 1
#             → odd blocks (1,3) use v1; even blocks (2,4) use v2
#             → each of 8 questions appears exactly twice
#
#   n/node = 1 (pool-4):  variant = 1 always (only one variant exists)
#             → each of 4 questions appears in every block (4× total)
#             → unavoidable for category 7
# ─────────────────────────────────────────────────────────────────
records = []
for b in range(N_BLOCKS):
    for cat, ntype, n_q in CATEGORIES:
        nodes = NB_NODES if ntype == 'NB' else B_NODES
        for node in nodes:
            if n_q == 4:
                q_num = b + 1              # blocks 0–3 → variants 1–4
            elif n_q == 2:
                q_num = (b % 2) + 1       # 0,2→1  1,3→2
            else:
                q_num = 1
            records.append({
                'block'        : b + 1,
                'category'     : cat,
                'question_code': f"{cat}{node}{q_num}"
            })

df = pd.DataFrame(records)

# ─────────────────────────────────────────────────────────────────
# VERIFICATION
# ─────────────────────────────────────────────────────────────────
errors = []

# 1. No within-block question repetition
for b, bdf in df.groupby('block'):
    dupes = bdf[bdf.duplicated('question_code')]
    if not dupes.empty:
        errors.append(f"Block {b} has duplicate questions: {dupes['question_code'].tolist()}")

# 2. Each block has exactly 36 questions
for b, bdf in df.groupby('block'):
    if len(bdf) != 36:
        errors.append(f"Block {b} has {len(bdf)} questions (expected 36)")

# 3. Question appearance counts match expected values
counts = df['question_code'].value_counts()
for cat, ntype, n_q in CATEGORIES:
    nodes    = NB_NODES if ntype == 'NB' else B_NODES
    expected = N_BLOCKS // n_q   # 4→1×  2→2×  1→4×
    for node in nodes:
        for q in range(1, n_q + 1):
            code   = f"{cat}{node}{q}"
            actual = counts.get(code, 0)
            if actual != expected:
                errors.append(f"{code}: expected {expected}×, got {actual}×")

# 4. All 4 nodes appear for each (block, category) pair
for (b, cat), bdf in df.groupby(['block', 'category']):
    cat_ntype  = next(t for c, t, _ in CATEGORIES if c == cat)
    expected_nodes = sorted(NB_NODES if cat_ntype == 'NB' else B_NODES)
    actual_nodes   = sorted(bdf['question_code'].str[1].tolist())
    if actual_nodes != expected_nodes:
        errors.append(f"Block {b} Cat {cat}: nodes {actual_nodes} ≠ expected {expected_nodes}")

if errors:
    print("VERIFICATION FAILED:")
    for e in errors: print(" •", e)
else:
    print("✓ No within-block question repetition")
    print("✓ All blocks have exactly 36 questions")
    print("✓ All question codes appear the expected number of times")
    print("✓ All 4 base nodes present for each (block, category) pair")

# ─────────────────────────────────────────────────────────────────
# SUMMARY STATS
# ─────────────────────────────────────────────────────────────────
print(f"\n── Questions per block: {len(df) // N_BLOCKS} ──")
print(f"── Total rows: {len(df)} ──\n")

print("── Question appearances across all blocks ──")
for n_q, label in [(4, "pool-16 (n/node=4)"), (2, "pool-8  (n/node=2)"), (1, "pool-4  (n/node=1)")]:
    expected = N_BLOCKS // n_q
    cats = [cat for cat, _, nq in CATEGORIES if nq == n_q]
    print(f"  {label}  categories {cats}  →  {expected}× each")

print("\n── Variant used per block (pool-8 and pool-16 categories) ──")
for b in range(1, N_BLOCKS + 1):
    bdf = df[df['block'] == b]
    sample_n4 = bdf[bdf['category'] == 1]['question_code'].tolist()
    sample_n2 = bdf[bdf['category'] == 2]['question_code'].tolist()
    print(f"  Block {b}  cat1(n4): {sample_n4}  cat2(n2): {sample_n2}")

# ─────────────────────────────────────────────────────────────────
# OUTPUT TABLE
# ─────────────────────────────────────────────────────────────────
out = df.sort_values(['block', 'category', 'question_code']).reset_index(drop=True)

print("\n── Counterbalancing table (first 18 rows) ──")
print(out.head(18).to_string(index=False))

out.to_csv('../data/counterbalancing_table_v2.csv', index=False)
print("\n✓ Table saved to counterbalancing_table_v2.csv")
