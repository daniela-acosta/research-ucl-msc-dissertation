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
A: B, C, D        E: B, F, H
B: A, C, E        F: E, G, H
C: A, B, D        G: D, F, H
D: A, C, G        H: E, F, G
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
| 2 | NB1WNB__NB2XB  | T1 | 8  | 2 | NB | Within NB vs cross-community boundary |
| 3 | NB1WB__NB1WNB  | T2 | 8  | 2 | NB | Within boundary vs within NB (both 1 step, both plausible) |
| 4 | B2WB__B2XNB    | T0 | 8  | 2 | B  | Within boundary vs cross-community NB (both 2 steps, 0 plausible) |
| 5 | B1WNB__B2WB    | T1 | 8  | 2 | B  | Within NB vs within boundary (from boundary base) |
| 6 | B1WNB__B2XNB   | T1 | 16 | 4 | B  | Within NB vs cross-community NB |
| 7 | B1XB__B2WB     | T1 | 4  | 1 | B  | Cross boundary vs within boundary |
| 8 | B1XB__B2XNB    | T1 | 8  | 2 | B  | Cross boundary vs cross-community NB |
| 9 | B1WNB__B1XB    | T2 | 8  | 2 | B  | Within NB vs cross boundary (both 1 step) |

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
- **Experiment library:** jsPsych (v7.3.4)
- **Language:** JavaScript / HTML / CSS
- **Data pipeline:** Python (planning scripts, counterbalancing, graph definition)

The experiment is built in `/experiment/`. Configuration should be centralised so that
timing, stimuli, block counts, question counts, and counterbalancing group can all be
changed from a single config file or object without touching trial logic.

### jsPsych CDN pattern
jsPsych is loaded via CDN (no bundler). Use **package name + version only** — no file path.
unpkg resolves to the correct browser build automatically via the package's `unpkg` field.

```html
<!-- core -->
<script src="https://unpkg.com/jspsych@7.3.4"></script>

<!-- plugins — same pattern, no file path -->
<script src="https://unpkg.com/@jspsych/plugin-html-keyboard-response@1.1.3"></script>
```

**Do not append a file path** (not `/jspsych.js`, not `/dist/index.js`, not `/dist/index.browser.min.js`).
Adding a path serves the wrong build and causes `jsPsychModule is not defined` / `initJsPsych is not defined` errors.

The JATOS integration pattern (all three required in every component):
1. `<script src="jatos.js"></script>` in `<head>`
2. `on_finish: () => jatos.startNextComponent()` inside `initJsPsych({...})`
3. `jsPsych.run(timeline)` called inside `jatos.onLoad(function() { ... })`

---

## Project Structure

```
/data/                        — CSV outputs (do not delete existing files, only add)
  2afc_question_candidates_v2.csv   — full 2AFC question pool with metadata
  counterbalancing_table.csv        — pre-generated trial assignment table (canonical source)
  (other CSVs from graph_definition.py)

/experiment/                  — jsPsych experiment (main build target)
  package.json
  data/                       — copies of CSVs needed at runtime (JATOS can't serve ../data/)
    counterbalancing_table.csv
    2afc_question_candidates_v2.csv
  components/                 — shared JS modules (IIFE pattern, no bundler)

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
- **Filenames must use lowercase `stimulus_`** — the code constructs paths as
  `stimulus_A.png` (lowercase s). macOS is case-insensitive so any casing works
  locally, but Mindprobe runs Linux which is case-sensitive — `Stimulus_A.png` causes
  a silent 404 on the server only.
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
| `trial_index_in_block` | 0-based trial index within the block |
| `question_code` | Question identifier, e.g. `3F1` |
| `question_number` | Sequential number within (base, category) group — the trailing digit of the code |
| `category` | Category number (1–9) |
| `comparison_pair_tag` | Full tag, e.g. `NB1WNB__NB2XB` |
| `comparison_type` | T0, T1, or T2 |
| `base_node` | Base node label |
| `option_left` | Destination node shown on the left |
| `option_right` | Destination node shown on the right |
| `left_is_option_a` | Boolean — whether the left option is optionA from the candidates CSV |
| `chosen_position` | `'left'` or `'right'`, or `null` if timed out |
| `chosen_node` | Node label of the chosen option, or `null` |
| `chose_plausible` | Boolean — whether the chosen option is the plausible one (T1 only); `null` for T0/T2 |
| `response` | Raw key pressed (`'f'` or `'j'`), or `null` if timed out |
| `rt` | Response time in ms, or `null` if timed out |
| `timed_out` | Boolean |
| `confidence_response` | Slider value (0–100) from the confidence judgement; written back into the 2AFC row by the confidence trial's `on_finish` |
| `confidence_rt` | Response time for the confidence judgement (ms) |
| `group` | Counterbalancing group (1–4) |
| `prolific_pid` | Prolific participant ID — **not yet recorded in trial data**; stored in `studySessionData` at consent and saved with demographics only |

---

## Deployment Mode

Currently building for **online deployment** only (Mindprobe/JATOS + Prolific).

An in-person mode (run locally on the researcher's computer, no Prolific) may be
added later. To keep that option open, isolate all Prolific-specific logic (URL
parameter capture, completion redirect) in clearly labelled, self-contained functions
rather than scattering it through component logic.

---

## Local Development

Components are tested by opening HTML files directly in a browser — no JATOS server
running. The setup that supports this:

- Every HTML component includes `<script src="jatos.js"></script>` in its `<head>`.
  On the JATOS server, JATOS intercepts requests for this path and serves its own
  real implementation automatically. Locally, `/experiment/jatos.js` is a **mock**
  that stubs the full JATOS API and logs all calls to the browser console.
- `studySessionData` and `batchSession` are in-memory only in the mock — they reset
  on page reload and do not persist across components when testing locally.
- Group assignment via `assignGroup()` will always pick group 1 on a fresh load
  (batch session starts empty). This is expected behaviour locally.
- When deploying to JATOS, the mock `jatos.js` can be left in the bundle — JATOS
  intercepts the request and serves its own version, ignoring the bundled file.
  Verify this holds for your JATOS version before first deployment.
- `Utils.getStimulusPath()` uses `jatos.studyAssetsUrl` (absolute URL) when running
  on a JATOS server, and falls back to a relative path (`./assets/...`) locally.
  This is necessary because Mindprobe's URL routing makes relative paths unreliable
  for assets. Stimulus filenames must use lowercase `stimulus_` prefix and uppercase
  node label (e.g. `stimulus_A.png`) — Linux is case-sensitive unlike macOS.

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
  E: ['B', 'F', 'H'],  F: ['E', 'G', 'H'],
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
| `practiceWalkLength` | 26 | Same as main task for now; adjust in config to change |
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

Practice structure (implemented in `practice.html`):
1. **Comprehension check (cover task)** — up to 2 attempts; correct answer revealed if
   both fail; participant may always continue regardless of outcome.
2. **Untimed cover task practice** — deterministic walk; feedback after each step.
3. **Timed cover task practice** — same walk, `stimulusDuration` ms limit; visual
   warning if no response given within the time limit (no audio).
4. **Comprehension check (2AFC)** — up to 2 attempts; if participant failed the cover
   check AND fails this one, `jatos.abortStudy()` is called; otherwise correct answer
   is revealed and they continue.
5. **Untimed 2AFC practice** — `CONFIG.practiceTwoAFCTrials`; feedback after each trial.
6. **Timed 2AFC practice** — same, `testMaxResponseTime` ms limit; feedback given.

A transition screen ("now with a time limit") separates steps 2→3 and 5→6.

**Implementation notes:**
- `buildCheck({ questionHtml, choices, correctIndex, revealHtml, onBothFailed })` — local
  helper in `practice.html` that builds a jsPsych `loopFunction` node (max 2 passes) +
  a conditional reveal node. Returns `{ nodes, passed() }` where `passed()` reads the
  closure at call time, so the 2AFC check can inspect the cover check outcome after it ran.
- Practice 2AFC positions (`optionLeft`/`optionRight`) are **pre-assigned** in
  `CONFIG.practiceTwoAFCTrials` — they are not randomised, so feedback is unambiguous.
  Only main-task 2AFC trials randomise left/right at runtime.
- Practice trial data is **not saved** — `on_finish` calls `jatos.startNextComponent()`,
  not `jatos.submitResultData()`.
- Practice stimuli use nodes I, J, K; images are named `stimulus_I.png` etc.

Practice walk length and number of practice 2AFC trials are separate configurable
variables (`practiceWalkLength`, `practiceQuestionsPerBlock`).

---

## Counterbalancing Table Loading

- The counterbalancing table is bundled inside the experiment directory at
  `/experiment/data/counterbalancing_table.csv` and loaded at runtime via `fetch()`
  at the start of the main task component
- The canonical source is `/data/counterbalancing_table.csv` (project root). If that
  file is ever regenerated, copy it into `/experiment/data/` as well
- Do **not** regenerate the table in JavaScript — the CSV is the source of truth
- JATOS can only serve files within the study's own directory — paths like `../data/`
  will 404. All assets must be inside `/experiment/`
- Filter rows by the participant's assigned group (stored in `jatos.studySessionData`)
  to get their specific 36-trial sequence
- Parse with a lightweight CSV parser (e.g. PapaParse); do not write a custom parser

---

## Breaks Between Blocks
Not included in the current build. Easy to add later as a self-paced screen between
blocks — keep this in mind when structuring the block loop.

---

## Known Issues / Things to Verify

### Category ordering — resolved
An earlier version of `config.js` had `categoryToPairTag` in the wrong order (not matching
`counterbalancing.py` or the design docs). This has been corrected by the researcher.
The canonical ordering is now in `config.js` and matches the counterbalancing table.

The previously flagged "category 6 missing candidates" issue was a consequence of this wrong
ordering — with the correct mapping, category 6 is `B1WNB__B2XNB` (pool 16, n_q=4), which
does have 4 candidate rows per boundary node, so codes `6X3` and `6X4` exist and resolve correctly.

---

## Open Design Questions (resolve before building affected components)

| Question | Affects |
|----------|---------|
| Response keys for cover task and 2AFC | Config, instructions |
