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

## Text Content and Stimuli

### Text (instructions, consent, debrief, demographics)
All participant-facing text is **lorem ipsum placeholder** for now. Use realistic
placeholder structure (e.g. a consent form with the right sections, instructions with
the right number of steps) but dummy text throughout. Final copy will be supplied later
and dropped in without structural changes. Do not spend time on wording.

### Stimuli
Node stimuli (the shapes shown during the learning phase) will be supplied as image
files later. For now use **placeholder images** — an HTML canvas-drawn shape, a
coloured div, or a simple SVG is fine. The placeholder should occupy the correct
screen region so layout can be validated without real assets.

- Stimuli are loaded by node label (A–H); the naming convention for final image files
  will be `stimulus_A.png`, `stimulus_B.png`, etc. — build the loader to expect this
- Do not hardcode stimuli inline; always load from a path defined in the config object

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

---

## Study Components

The experiment is structured as a sequence of JATOS components, each a separate HTML
page. They share logic via common JS modules in `/experiment/components/`.

### Component sequence
1. **Consent** — informed consent form; study ends immediately if declined
2. **Demographics** — age, gender, handedness, native language, normal/corrected vision
3. **Instructions** — explains the cover task (symmetry judgement) only; does NOT
   mention the graph, communities, or transition structure
4. **Practice** — shortened version of the main task (fewer learning steps, fewer
   test questions); may give feedback; data saved but analysed separately
5. **Main task** — 4 blocks of learning phase + test phase (see block structure above);
   no feedback; all trial data saved to JATOS
6. **Debrief** — reveals the true purpose of the study; Prolific completion redirect

### Shared modules
Practice and main task share the same underlying learning-phase and test-phase logic,
implemented as reusable JS modules in `/experiment/components/`. They differ only in
parameters (number of steps, number of questions, whether feedback is shown). Do not
duplicate trial logic between components — parameterise it.

---

## Recruitment and Prolific Integration

- Participants are recruited via **Prolific**
- Prolific appends three URL parameters when a participant clicks the study link:
  `PROLIFIC_PID`, `STUDY_ID`, `SESSION_ID` — capture all three at study start and
  store them with the data
- At the end of the debrief component, redirect to the Prolific **completion URL**
  so participants are automatically credited
- The completion URL is a configurable parameter (do not hardcode it)

---

## Group Assignment and Dropout Handling

### Assignment strategy
- Use the **JATOS Batch Session** for group assignment to ensure balanced group sizes
  even with a small N (~40) and potential dropout
- On study start, the consent component reads the current group counts from
  `jatos.batchSession`, assigns the participant to the least-filled group, and
  increments that group's counter atomically
- Assigned group is then stored in `jatos.studySessionData` and read by all subsequent
  components

### Dropout
- No special recovery for incomplete participants — they are excluded from analysis
- JATOS records partial data automatically; incomplete runs are identifiable by absence
  of the debrief component's result data

---

## Test Phase

- Questions within each block are **randomised in order** at runtime (Fisher-Yates shuffle)
- Option position (left/right on screen) is **randomised per trial** at runtime
- Maximum response time is **3000 ms** (configurable via `testMaxResponseTime`)
- If no response is given within the time limit, record as a timeout (`response: null,
  rt: null, timed_out: true`) and advance automatically
- Questions are drawn from the counterbalancing table filtered by participant group and
  current block number

---

## Data Recording

### Per learning phase step
Record for every node shown during the random walk:

| Field | Description |
|-------|-------------|
| `block` | Block number (1–4) |
| `step` | Step index within the walk |
| `node` | Node label shown (A–H) |
| `cover_response` | Participant's symmetry judgement response |
| `cover_rt` | Response time for cover task |

The full walk sequence for each block is also stored as a flat array in
`jatos.studySessionData` for use in later components if needed.

### Per 2AFC trial
| Field | Description |
|-------|-------------|
| `block` | Block number (1–4) |
| `trial` | Trial index within block (1–9) |
| `question_code` | Question identifier, e.g. `3F1` |
| `category` | Category number (1–9) |
| `comparison_pair_tag` | Full tag, e.g. `NB1WNB__NB2XB` |
| `comparison_type` | T0, T1, or T2 |
| `base_node` | Base node label |
| `option_left` | Destination node shown on the left |
| `option_right` | Destination node shown on the right |
| `response` | `'left'` or `'right'`, or `null` if timed out |
| `rt` | Response time in ms, or `null` if timed out |
| `timed_out` | Boolean |
| `group` | Counterbalancing group (1–4) |
| `prolific_pid` | Prolific participant ID |

---

## Deployment Mode

Currently building for **online deployment** only (Mindprobe/JATOS + Prolific).

An in-person mode (run locally on the researcher's computer, no Prolific) may be
added later. To keep that option open, isolate all Prolific-specific logic (URL
parameter capture, completion redirect) in clearly labelled, self-contained functions
rather than scattering it through component logic.

---

## Random Walk

The learning phase sequence is generated client-side by a JS function. Spec:

- Input: adjacency list (from config), number of steps (from config)
- Output: array of node labels, e.g. `['A', 'C', 'B', 'E', ...]`
- At each step, pick uniformly at random from the current node's neighbours
- Starting node is chosen uniformly at random from all 8 nodes
- The full sequence is recorded per participant (see Data Recording below)

The adjacency list is fixed and small — hardcode it in the config file:
```js
adjacency: {
  A: ['B', 'C', 'D'],  B: ['A', 'C', 'E'],
  C: ['A', 'B', 'D'],  D: ['A', 'C', 'G'],
  E: ['B', 'F', 'G'],  F: ['E', 'G', 'H'],
  G: ['D', 'F', 'H'],  H: ['E', 'F', 'G']
}
```

---

## Timing and Trial Parameters

All values live in the central config object — do not hardcode them in trial logic.

| Parameter | Value | Notes |
|-----------|-------|-------|
| `stimulusDuration` | 2000 ms | Stimulus display including cover task response window |
| `interStimulusInterval` | 200 ms | Blank screen between learning phase steps (no fixation cross) |
| `walkLength` | 26 | Number of steps per learning phase block (main task) |
| `practiceWalkLength` | TBD | Shorter walk for practice block — set as separate config var |
| `testMaxResponseTime` | 3000 ms | Max time to respond in 2AFC; record timeout if no response |
| `numBlocks` | 4 | Number of learning + test block pairs |
| `questionsPerBlock` | 9 | One per comparison category |

### Response inputs
Response keys for both the cover task and the 2AFC are **configurable variables** —
assign simple defaults for initial build and iterate during piloting. Do not hardcode
key assignments anywhere other than the config object.

### Fullscreen
The experiment enforces fullscreen on start using the jsPsych fullscreen plugin.
Participants must accept fullscreen to proceed.

### What participants see
- Participants **never see node labels** (A–H) or any internal tags — these are for
  data recording only
- During the learning phase, each node is represented by its **stimulus image**
  (placeholder for now; final files will be `stimulus_A.png` etc.)
- During the 2AFC test phase, the base node and two destination options are shown
  as stimulus images only

### Practice block
Based on Kaper & Peters (2025, preprint), the practice phase uses **dedicated practice
stimuli** (nodes I, J, K — entirely separate from the main experiment nodes A–H) with a
**fully deterministic walk** (I→J→K→I→J→K...). This ensures zero contamination of
learning in the main task.

Practice structure:
1. **Comprehension check (cover task)** — question verifying understanding of the
   symmetry judgement (e.g. "what should you do when a shape appears on screen?");
   two attempts allowed; correct answer revealed if both attempts fail; participant
   may continue regardless
2. **Untimed cover task practice** — short deterministic walk with practice stimuli;
   feedback given after each trial on cover task correctness
3. **Timed cover task practice** — same deterministic walk, timed (same `stimulusDuration`
   as main task); auditory/visual feedback if no response within time limit
4. **Comprehension check (2AFC)** — question verifying understanding of the forced
   choice (e.g. "in each question, what are you being asked to judge?"); two attempts
   allowed; if participant failed the cover task comprehension check AND fails this one
   after two attempts, they are blocked from continuing; otherwise correct answer
   revealed and they may continue
5. **Untimed 2AFC practice** — a few practice 2AFC trials using the deterministic practice
   stimuli; feedback given on correctness after each trial
6. **Timed 2AFC practice** — same, but timed (same `testMaxResponseTime` as main task);
   feedback given if answered in time

Practice walk length and number of practice test trials are separate configurable variables.
Practice trial data is **not saved**.

The practice stimuli (I, J, K) need placeholder images like the main stimuli; name them
`stimulus_I.png` etc. for consistency.

---

## Counterbalancing Table Loading

- The counterbalancing table (`/data/counterbalancing_table.csv`) is **bundled with
  the study files** and loaded at runtime via `fetch()` at the start of the main task
  component
- Do **not** regenerate the table in JavaScript — the CSV is the source of truth
- Filter rows by the participant's assigned group (stored in `jatos.studySessionData`)
  to get their specific 36-trial sequence
- Parse with a lightweight CSV parser (e.g. PapaParse); do not write a custom parser

---

## Breaks Between Blocks
Not included in the current build. Easy to add later as a self-paced screen between
blocks — keep this in mind when structuring the block loop.

---

## Open Design Questions (resolve before building affected components)

| Question | Affects |
|----------|---------|
| Response keys for cover task and 2AFC | Config, instructions |
