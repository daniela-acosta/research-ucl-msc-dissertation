# Graph Learning Experiment — Project Context

This file gives Claude Code the full context needed to work on this project.
Read it at the start of every session before touching any files.

---

## Research Overview

This is a cognitive neuroscience dissertation experiment studying **how statistical
learning transitions from implicit to explicit knowledge** — specifically, trying to
capture the "aha moment" when a participant becomes consciously aware of a community
structure they have been implicitly learning. Supervised by Megan Peters.

The paradigm is **graph learning via random walk**, using a community-structured graph.
Participants are exposed to a sequence of nodes (with a cover task) and then tested on
their knowledge of transition probabilities via 2-Alternative Forced Choice (2AFC) questions.

---

## Graph Structure

8 nodes across 2 communities. The graph is **3-regular** (every node has exactly 3 edges).

```
Community 1: A (NB), B (boundary), C (NB), D (boundary)
Community 2: E (boundary), F (NB), G (boundary), H (NB)
```

**Node types:**
- **Non-Boundary (NB):** A, C, F, H — connected to all 3 other nodes in their community
- **Boundary (B):** B, D, E, G — connected to 2 nodes in their community (all except
  the other boundary node) plus 1 cross-community boundary node

**Cross-community edges:** B↔E and D↔G (bijection — symmetric structure)

**Adjacency (each node has exactly 3 neighbours):**
```
A: B, C, D        E: B, F, G
B: A, C, E        F: E, G, H
C: A, B, D        G: D, F, H
D: A, C, G        H: E, F, G (wait — H: F, G, E... same thing)
```

The graph is defined programmatically in `/planning/graph_definition.py` using networkx.
**Do not redefine the graph manually elsewhere** — import or regenerate from that file.

---

## Experiment Structure

### Phases (repeated across blocks)
1. **Learning phase:** Random walk over the graph. Each node is shown as a stimulus
   with a **cover task** (symmetry judgement — participant judges whether the displayed
   shape is symmetrical). This masks the true learning objective.
2. **Test phase:** 2AFC questions — participant sees a base node and two possible
   destination nodes, and judges which transition is more likely.

### Block structure
- **4 blocks** total, each containing one learning phase followed by one test phase
- Each test phase has **9 questions** (one per comparison category)
- **36 questions total per participant**, with no repetition across blocks

---

## 2AFC Question Design

### Question notation
Each question is identified as `[category][node][question_number]`, e.g. `1A2`.

- **Category (1–9):** the comparison type (see table below)
- **Node:** the representative base node used (rotated across blocks/groups)
- **Question number:** index within that category × node combination

### The 9 included comparison categories

| # | Tag | Type | Pool | n/node | Base type | Description |
|---|-----|------|------|--------|-----------|-------------|
| 1 | NB1WB__NB2XB   | T1 | 16 | 4 | NB | Within-community boundary vs cross-community boundary (1 step vs 2 steps) |
| 2 | NB1WB__NB1WNB  | T2 | 8  | 2 | NB | Within boundary vs within NB (both 1 step, both plausible) |
| 3 | NB1WNB__NB2XB  | T1 | 8  | 2 | NB | Within NB vs cross-community boundary |
| 4 | B1WNB__B2WB    | T1 | 8  | 2 | B  | Within NB vs within boundary (from boundary base) |
| 5 | B1WNB__B2XNB   | T1 | 16 | 4 | B  | Within NB vs cross-community NB |
| 6 | B2WB__B2XNB    | T0 | 8  | 2 | B  | Within boundary vs cross-community NB (both 2 steps, 0 plausible) |
| 7 | B1XB__B2WB     | T1 | 4  | 1 | B  | Cross boundary vs within boundary |
| 8 | B1WNB__B1XB    | T2 | 8  | 2 | B  | Within NB vs cross boundary (both 1 step) |
| 9 | B1XB__B2XNB    | T1 | 8  | 2 | B  | Cross boundary vs cross-community NB |

**Comparison type (T0/T1/T2):** number of plausible options in the pair (0, 1, or 2).
T1 questions are the most informative for learning analysis; T0 and T2 are included
to capture sensitivity differences between within vs cross-community transitions.

**NB categories (1–3)** use base nodes A, C, F, H.
**B categories (4–9)** use base nodes B, D, E, G.

The full question candidate list with all metadata is in `/data/2afc_question_candidates_v2.csv`.
Columns: `base`, `base_is_boundary`, `base_community`, `optionA_dest`, `optionA_plausible`,
`optionA_steps`, `optionA_within_code`, `optionA_same_community`, `optionA_dest_is_boundary`,
`optionA_tag`, `optionB_dest`, `optionB_plausible`, `optionB_steps`, `optionB_within_code`,
`optionB_same_community`, `optionB_dest_is_boundary`, `optionB_tag`, `comparison_type`,
`comparison_pair_tag`.

---

## Counterbalancing Design

### Groups and node rotation
- **4 counterbalancing groups** (Group 1–4), loaded from CSV at runtime
- Each participant is assigned to one group
- Within a block, each NB category uses a **different NB node** (diversity within block)
- Node rotation formula: `node_index = (group + block + category_rank) % 4`
- Question number formula: `question_number = (block % n_questions_per_node) + 1`

### Question frequency across groups
| Category pool size | Appearances per question across all groups |
|--------------------|------------------------------------------|
| 16 questions (n_q=4) | 1× |
| 8 questions (n_q=2)  | 2× |
| 4 questions (n_q=1)  | 4× (category 7 only — unavoidable) |

### Counterbalancing table
The pre-generated table is in `/data/counterbalancing_table.csv`.
Columns: `trial`, `block`, `category`, `Group_1`, `Group_2`, `Group_3`, `Group_4`.
Each cell contains the question code (e.g. `3F1`) for that group × block × category slot.
This CSV is the **source of truth** for trial assignment — do not hardcode trial sequences.

The script that generated it is `/planning/counterbalancing.py`.

### Option position (left/right)
Option A vs Option B position (left/right on screen) should be **randomised** per trial
at runtime. This is not pre-counterbalanced — handle it dynamically in jsPsych.

---

## Tech Stack

- **Experiment platform:** JATOS (self-hosted or Mindprobe)
- **Experiment library:** jsPsych (v7+)
- **Language:** JavaScript / HTML / CSS
- **Data pipeline:** Python (planning scripts, counterbalancing, graph definition)

The experiment is built in `/experiment/`. Configuration should be centralised so that
timing, stimuli, block counts, question counts, and counterbalancing group can all be
changed from a single config file or object without touching trial logic.

---

## Project Structure

```
/data/                        — CSV outputs (do not delete existing files, only add)
  2afc_question_candidates_v2.csv   — full 2AFC question pool with metadata
  counterbalancing_table.csv        — pre-generated trial assignment table
  (other CSVs from graph_definition.py)

/experiment/                  — jsPsych experiment (main build target)
  package.json
  components/                 — (empty, for reusable jsPsych components/plugins)

/planning/                    — Python analysis and design scripts
  counterbalancing.py         — generates counterbalancing_table.csv
  graph_definition.py         — defines graph, generates question candidates
  requirements.txt
  venv/

/test_experiment/             — scratch JATOS test (not important, ignore)

CLAUDE.md                     — this file
.gitignore
```

---

## Key Design Decisions and Constraints

1. **No question repetition within a participant.** The same question code must never
   appear twice for the same participant across blocks.

2. **Counterbalancing is loaded from CSV, not hardcoded.** The experiment reads
   `/data/counterbalancing_table.csv` and filters by the participant's assigned group.

3. **Questions are randomised within each block** at runtime (not pre-ordered).

4. **Option position (left/right) is randomised** per trial at runtime.

5. **The cover task is symmetry judgement.** During the learning/random walk phase,
   participants see a shape alongside each node and judge symmetry. This masks the
   learning objective. The node identity and the symmetry task response should both
   be recorded.

6. **All configurable parameters** (timings, number of blocks, stimuli paths, node
   labels, etc.) should live in a single config object/file. Do not scatter magic
   numbers through trial definitions.

7. **Data must be JATOS-compatible.** Use `jatos.studySessionData` or
   `jatos.resultData` for storing trial-level data; do not rely on browser storage.

8. **Do not modify files in `/data/`** unless explicitly asked. New CSVs can be added.

9. **The `/planning/` directory is Python-only.** Do not add JS files there.

---

## Terminology Reference

| Term | Meaning |
|------|---------|
| NB node | Non-boundary node (A, C, F, H) — fully within-community connections |
| B node | Boundary node (B, D, E, G) — one cross-community edge |
| Within (W) | Transition stays inside the same community |
| Cross (X) | Transition goes to the other community |
| T0/T1/T2 | Number of plausible options in a 2AFC pair (0, 1, or 2) |
| 2AFC | Two-Alternative Forced Choice — "which transition is more likely?" |
| Cover task | Symmetry judgement shown during learning phase to mask true objective |
| Block | One learning phase + one test phase |
| Group | Counterbalancing group (1–4), determines which question variants a participant sees |
