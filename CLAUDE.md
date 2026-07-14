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

The graph is defined programmatically in `/data_analysis/graph_definition.py` using networkx.
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
- Each test phase has **36 questions** (4 per comparison category — all 4 base nodes used)
- **144 questions total per participant**; questions from pool-8 categories repeat across blocks (see Counterbalancing Design)

---

## 2AFC Question Design

### Question notation
Each question is identified as `[category][node][question_number]`, e.g. `1A2`.

- **Category (1–9):** the comparison type (see table below)
- **Node:** the base node used (all 4 eligible nodes appear each block)
- **Question number:** variant index within that category × node combination (1–4 for pool-16; 1–2 for pool-8; always 1 for pool-4)

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

The full question candidate list with all metadata is in `/data/2afc_question_candidates_v3.csv`.
Columns: `base`, `base_is_boundary`, `base_community`, `optionA_dest`, `optionA_plausible`,
`optionA_steps`, `optionA_within_code`, `optionA_same_community`, `optionA_dest_is_boundary`,
`optionA_tag`, `optionB_dest`, `optionB_plausible`, `optionB_steps`, `optionB_within_code`,
`optionB_same_community`, `optionB_dest_is_boundary`, `optionB_tag`, `comparison_type`,
`comparison_pair_tag`, `question_number`.

---

## Counterbalancing Design

There are **no counterbalancing groups**. All participants see the same fixed set of
questions per block; the random walk, dynamic stimulus assignment (Config 3/4), and
within-block question ordering provide participant-level variability.

### 36 questions per block — assignment rules

Each block presents all 4 eligible base nodes for every category (4 nodes × 9 categories
= 36 questions). The specific question variant assigned to each (block, category, node)
slot follows these rules, determined by pool size:

| Pool | Categories | Per-block questions | Across-block rule | Total appearances |
|------|-----------|--------------------|--------------------|-------------------|
| 16 (n/node = 4) | 1, 6 | 4 (one variant per node) | Block 1→v1, Block 2→v2, Block 3→v3, Block 4→v4 | 1× each |
| 8 (n/node = 2) | 2, 3, 4, 5, 8, 9 | 4 (one variant per node) | Odd blocks (1,3)→v1, Even blocks (2,4)→v2 | 2× each |
| 4 (n/node = 1) | 7 | 4 (same 4 every block) | Repeats in all 4 blocks | 4× each |

**No question repeats within a block.** The pool-4 (category 7) questions repeat across
blocks (unavoidable — only 4 unique questions exist for that category).

### Counterbalancing table
The pre-generated table is in `/data/counterbalancing_table.csv` (canonical source) and
copied to `/experiment/data/counterbalancing_table.csv` for JATOS serving.
Columns: `block`, `category`, `question_code`.
144 rows total (36 per block × 4 blocks). No Group columns.
This CSV is the **source of truth** for trial assignment — do not hardcode trial sequences.

The script that generated it is `/data_analysis/counterbalancing.py`.

### Option position (left/right)
Option A vs Option B position (left/right on screen) is **randomised** per trial at
runtime. This is not pre-counterbalanced — handled dynamically in jsPsych.

---

## Stimulus Counterbalancing

Each participant is randomly assigned a **stimulus config** (3 or 4), independently of
their counterbalancing group. The config controls how fractal symmetry type maps onto
boundary node positions.

### Constraints (both configs)
- Each community must have exactly **2 symmetrical (S) and 2 asymmetrical (A)** nodes.
- Both communities must have **one S and one A boundary node**.

### Config 3
The two cross-community boundary pairs (B↔E and D↔G) are the **same** symmetry type
as each other — i.e. B and E are both S (or both A), and D and G are both S (or both A).

### Config 4
The two cross-community boundary pairs are **different** symmetry types from each other —
i.e. B and E are opposite types, and D and G are opposite types.

### Assignment algorithm (`Utils.assignStimuli(config)`)
1. Randomly pick B's type (S or A, 50/50). D is the opposite (community 1 needs 1S, 1A boundary).
2. Derive E and G from B and D using the config rule above.
3. Randomly assign community 1 NB nodes (graph nodes A and C) to 1S + 1A.
4. Randomly assign community 2 NB nodes (graph nodes F and H) to 1S + 1A.
5. Shuffle `CONFIG.stimuliS` and `CONFIG.stimuliA` independently, then assign specific
   fractal filenames to nodes in order.

Returns `{ map, typeMap }`:
- `map` — `{ A: 'fractal19_S.png', B: 'fractal5_A.png', ... }` stored in `studySessionData`
- `typeMap` — `{ A: 'S', B: 'A', ... }` stored in `studySessionData` for analysis

### Session data keys (set at consent)
| Key (`CONFIG.sessionKeys.*`) | Value |
|------------------------------|-------|
| `stimulusConfig` | `3` or `4` |
| `stimulusMap` | `{ A: filename, B: filename, … }` |
| `stimulusTypeMap` | `{ A: 'S'/'A', B: 'S'/'A', … }` |

Note: `group` key has been removed — there are no counterbalancing groups.

`stimulusConfig` must be recorded in every participant's result data.

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
  2afc_question_candidates_v3.csv   — full 2AFC question pool with metadata (includes question_number column)
  counterbalancing_table.csv        — pre-generated trial assignment table (canonical source; 144 rows, no groups)
  results/                          — raw JATOS result folders for the main experiment
    combined_raw.csv                — output of load_data.py
    test_trials.csv                 — output of preprocess.py
    learning_trials.csv             — output of preprocess.py

/experiment/                  — jsPsych experiment (main build target)
  jatos.js                    — mock JATOS API for local development
  config.js                   — all tunable parameters (single source of truth)
  assets/                     — stimulus images and CSS
    fractal*_S.png / fractal*_A.png  — selected real fractals (8 total)
    stimulus_I/J/K.png        — placeholder practice stimuli (not yet finalised)
  data/                       — runtime CSVs (JATOS can't serve ../data/)
    counterbalancing_table.csv
    2afc_question_candidates_v3.csv
  components/                 — shared JS modules (IIFE pattern, no bundler)
    utils.js
    learning-phase.js
    test-phase.js

/data_analysis/               — Python and R analysis scripts (renamed from /planning/)
  scripts/
    load_data.py              — reads JATOS result folders → combined_raw.csv
    preprocess.py             — cleans types, derives accuracy/confidence_z → test/learning CSVs
    load_ratings.py           — reads symmetry rating results → ratings.csv
    generate_ratings_viz.py   — generates test_experiment/ratings_viz.html
    analyze_ratings.R         — ggplot2 dot plots of symmetry ratings
  venv/
  requirements.txt

/test_experiment/             — standalone symmetry rating experiment (stimulus selection tool)
  rating.html                 — jsPsych experiment: show each fractal, rate 1–5 symmetry
  jatos.js                    — local dev mock (copy of experiment/jatos.js + endStudy)
  stimuli/                    — all candidate fractal images (40 total, _S and _A variants)
  results/                    — JATOS result folders from rating runs
    ratings.csv               — combined output from load_ratings.py
  ratings_viz.html            — generated visualisation (images + dot strips, sorted by mean)

CLAUDE.md                     — this file
.gitignore
```

---

## Key Design Decisions and Constraints

1. **No question repetition within a participant.** The same question code must never
   appear twice for the same participant across blocks.

2. **Trial sequence is loaded from CSV, not hardcoded.** The experiment reads
   `/experiment/data/counterbalancing_table.csv` at runtime. No group filtering — all
   participants receive the same question set per block.

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

9. **The `/data_analysis/` directory is Python/R only.** Do not add JS files there.

10. **Stimulus assignment is random at runtime** — node A does not always show the same
    fractal. The node→fractal map is generated at consent and stored in `studySessionData`.
    Never hardcode a node-to-image mapping anywhere other than the assignment functions in
    `utils.js`.

---

## Text Content and Stimuli

### Text (instructions, consent, debrief, demographics)
All participant-facing text is **lorem ipsum placeholder** for now. Use realistic
placeholder structure (e.g. a consent form with the right sections, instructions with
the right number of steps) but dummy text throughout. Final copy will be supplied later
and dropped in without structural changes. Do not spend time on wording.

### Stimuli

**Final stimuli have been selected** from a pilot symmetry-rating experiment (see
`/test_experiment/`). The 8 selected fractals, split by symmetry type:

| Type | Files |
|------|-------|
| Symmetrical (S) | `fractal19_S.png`, `fractal9_S.png`, `fractal20_S.png`, `fractal10_S.png` |
| Asymmetrical (A) | `fractal5_A.png`, `fractal15_A.png`, `fractal4_A.png`, `fractal6_A.png` |

These files are in `experiment/assets/`. They are defined in `CONFIG.stimuliS` and
`CONFIG.stimuliA` and must not be renamed — the filenames encode the symmetry type
used by `assignStimuli()`.

**Stimulus assignment is dynamic** (not static `stimulus_A.png` → node A). At study
start (consent component), `Utils.assignStimulusConfig()` and `Utils.assignStimuli()`
generate a node→fractal mapping that is stored in `jatos.studySessionData`. All
subsequent components call `Utils.getStimulusPath(node)` which looks up the assigned
fractal filename for that node from session data.

**Practice stimuli** (nodes I, J, K) still use the placeholder `stimulus_I.png` pattern
since practice fractals have not yet been selected. `getStimulusPath()` falls back to
this pattern for any node not found in the session map.

**Linux case-sensitivity:** Mindprobe runs Linux. File paths are case-sensitive there
but not on macOS. Always keep filenames exactly as copied — do not rename or re-case them.

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
| Stimulus config | Config 3 or 4 — determines how S/A fractal types map onto boundary node positions |
| S / A | Symmetrical / Asymmetrical — the two fractal variants used as stimuli |
| stimulus_map | Session data key holding the runtime node→fractal filename assignment |

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

- Participants are recruited via **Prolific** using a **General Single** worker link
- Prolific appends three URL parameters when a participant clicks the study link:
  `PROLIFIC_PID`, `STUDY_ID`, `SESSION_ID` — read via `jatos.urlQueryParameters`
  (falls back to `window.location.search` for local dev)
- All three are written to `jatos.studySessionData` AND submitted as the first result
  data entry in `consent.html`, so the JATOS record is linkable to Prolific even if
  the participant drops out before completing any trials
- Three distinct Prolific completion paths are supported (see table below)
- Completion URLs are configurable in `config.js` — do not hardcode them

### Preview / admin mode

The full flow can be tested without a real Prolific session. `previewMode` is set to
`true` in `jatos.studySessionData` when any of the following is detected at consent:

- `jatos.workerType` is `'Jatos'` (JATOS admin "Run" button) or `'Preview'`
- `PROLIFIC_PID` URL parameter equals `CONFIG.previewPID` (`'PREVIEW'`)

In preview mode `Utils.endStudyRoute()` calls `jatos.endStudy()` instead of
`jatos.endStudyAndRedirect()`, and the debrief button reads "Finish (preview mode)".

### Completion paths

All exits call `Utils.endStudyRoute(url)` which respects preview mode automatically.
The Prolific redirect URL for each path is configured in `config.js`.

| Exit type | Trigger | Code shown | Config key | Prolific action | Payment |
|-----------|---------|-----------|-----------|-----------------|---------|
| **Full completion** | Participant finishes debrief | `COMPLETE` | `prolificCompletionURL` | Awaiting review (manual approve) | Full reward |
| **Declined consent** | Clicks "I do not wish to participate" on consent form | `SCREENOUT_COMPREHENSION` | `prolificScreenOutURL` | Screen-out (auto) | Screen-out reward |
| **Vision eligibility fail** | Reports uncorrected visual impairment in demographics | `SCREENOUT_COMPREHENSION` | `prolificScreenOutURL` | Screen-out (auto) | Screen-out reward |
| **Comprehension check fail** | Fails both comprehension checks (cover AND 2AFC) twice each in practice | `SCREENOUT_COMPREHENSION` | `prolificScreenOutURL` | Screen-out (auto) | Screen-out reward |
| **Attention fail** | Misses 3+ consecutive trials or >50% in a block (learning or test phase) | `EARLY_EXIT_ATTENTION` | `prolificAttentionExitURL` | Awaiting review (manual) | Prorated (manual) |
| **Missing PID** | Arrived without Prolific URL params and not a preview/admin worker | — | — | Abort (`jatos.abortStudy`), no redirect | None |

The three completion codes (`COMPLETE`, `SCREENOUT_COMPREHENSION`, `EARLY_EXIT_ATTENTION`)
must be configured identically in the Prolific study creation flow. The Prolific redirect
URL for each action is then pasted into the corresponding `config.js` key.

**Payment notes:**
- All five redirecting exits are paid — none are grounds for rejection
- `SCREENOUT_COMPREHENSION` exits auto-process via Prolific's native screen-out at a
  fixed small reward set when the study is created
- `COMPLETE` and `EARLY_EXIT_ATTENTION` both land in "Awaiting review" for manual approval
  (UCL lab policy is to manually approve all completions)
- `EARLY_EXIT_ATTENTION` pay is prorated based on which block the participant reached
  (logged as `exit_block` in the JATOS result data for that component)
- Analysis-stage exclusions (RT CV, confidence-slider correlation, etc.) are entirely
  separate from payment — they affect whether data is used, not whether the participant is paid

### Dropout

- No special recovery for incomplete participants who close the browser mid-task —
  they are excluded from analysis
- JATOS records partial data automatically; incomplete runs are identifiable by absence
  of the debrief component's result data, and linkable to Prolific via the PID written
  at the start of consent

---

## Test Phase

- Questions within each block are **randomised in order** at runtime (Fisher-Yates shuffle)
- Option position (left/right on screen) is **randomised per trial** at runtime
- Maximum response time is **3000 ms** (configurable via `testMaxResponseTime`)
- If no response is given within the time limit, record as a timeout (`response: null,
  rt: null, timed_out: true`) and advance automatically
- Questions are drawn from the counterbalancing table filtered by block number (no group column)

---

## Exclusion Criteria

Participants are excluded mid-experiment if their miss pattern in either phase exceeds
the configured thresholds. Practice is never checked.

### Rules (configured in `CONFIG.exclusion`)

| Phase    | Rule                    | Default | Checked when | Description |
|----------|-------------------------|---------|--------------|-------------|
| Learning | `maxConsecutiveMisses`  | 3       | After every trial | N unanswered trials in a row |
| Learning | `maxMissRatePerBlock`   | 0.5     | End of block only | >50 % of trials missed in the completed block |
| Test     | `maxConsecutiveMisses`  | 3       | After every trial | N unanswered trials in a row |
| Test     | `maxMissRatePerBlock`   | 0.5     | End of block only | >50 % of trials missed in the completed block |

Set either value to `null` to disable that check. The two rules are evaluated independently
and **either** triggers exclusion.

The miss rate check is deferred until the block is fully complete (i.e. until
`blockTrials.length >= CONFIG.walkLength` for learning, or `>= CONFIG.questionsPerBlock`
for test) — this prevents a single early miss from producing a misleading 100% rate.

### What happens on exclusion

1. A screen is shown with the `EARLY_EXIT_ATTENTION` completion code and an **OK button**
   (participant must acknowledge)
2. On click:
   - Exit data is submitted: `{ exit_type: 'attention_fail', exit_phase: 'learning'|'test', exit_block: N }`
   - `Utils.endStudyRoute(CONFIG.prolificAttentionExitURL)` is called — redirects the
     participant to the Prolific **awaiting-review** URL (or calls `jatos.endStudy()` in
     preview mode)
   - `jsPsych.endExperiment()` stops the timeline
3. The participant is redirected to Prolific with the `EARLY_EXIT_ATTENTION` code; their
   submission lands in the **Awaiting review** state for manual researcher action

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
| `confidence_response` | Slider value (0–100) from the confidence judgement; `null` if timed out; written back into the 2AFC row by the confidence trial's `on_finish` |
| `confidence_rt` | Response time for the confidence judgement (ms); `null` if timed out |
| `confidence_timed_out` | Boolean — whether the confidence trial exceeded `CONFIG.confidence.maxResponseTime` |
| `stimulus_config` | Stimulus counterbalancing config assigned to this participant (3 or 4) |
| `prolific_pid` | Prolific participant ID — **not yet recorded in trial data**; stored in `studySessionData` at consent and saved with demographics only |

### Confidence trial rows
Each 2AFC trial is followed by a separate confidence slider trial in the raw jsPsych data.
These rows have `trial_type_label: 'confidence'` and contain `response` (slider value 0–100,
or `null` if timed out) and `rt`. The time limit is `CONFIG.confidence.maxResponseTime`
(default 5000 ms); set to `null` to remove the limit.

The confidence values are also written back into the preceding 2AFC row as
`confidence_response`, `confidence_rt`, and `confidence_timed_out`, so analysis can work
from the 2AFC rows alone.

In practice (`giveFeedback: true`), a 800 ms warning ("Too slow! Please rate your
confidence before time runs out.") appears immediately after a timed-out confidence trial,
before the 2AFC correct/incorrect feedback.

Filter by `trial_type_label` to separate the four row types: `'learning'`, `'isi'`,
`'test'`, `'confidence'`.

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
- There are no counterbalancing groups — `assignGroup()` has been removed. The batch session
  is only used for stimulus config (3/4) balancing.
- When deploying to JATOS, the mock `jatos.js` can be left in the bundle — JATOS
  intercepts the request and serves its own version, ignoring the bundled file.
  Verify this holds for your JATOS version before first deployment.
- `Utils.getStimulusPath(node)` uses `jatos.studyAssetsUrl` (absolute URL) when running
  on a JATOS server, and falls back to a relative path (`./assets/...`) locally.
  For main nodes (A–H) it looks up the assigned fractal filename from
  `studySessionData.stimulus_map`; for practice nodes (I–K) it falls back to
  `stimulus_I.png` etc. Because `studySessionData` resets on page reload locally, the
  stimulus map won't be present when opening a mid-study component directly — images
  will fall back to the placeholder pattern, which is expected behaviour during development.

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
| `walkLength` | 48 | Number of steps per learning phase block (main task) |
| `practiceWalkLength` | 26 | Same as main task for now; adjust in config to change |
| `testMaxResponseTime` | 3000 ms | Max time to respond in 2AFC; record timeout if no response |
| `numBlocks` | 4 | Number of learning + test block pairs |
| `questionsPerBlock` | 36 | 4 per comparison category (all 4 base nodes × 9 categories) |

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
- Filter rows by block number only — no group column exists
- Parse with a lightweight CSV parser (e.g. PapaParse); do not write a custom parser

---

## Audio and Visual Feedback

Both the learning and test phases provide immediate feedback on keypresses and timeouts.
All audio is generated via the Web Audio API (no audio files required) and all functions
live in `Utils` so both phases share a single `AudioContext`.

### Keypress feedback (both phases)
- **Sound**: `Utils.playKeyTone()` — 660 Hz sine wave, 50 ms, soft fade-out
- **Visual**: the label of the pressed key (`F — Symmetric` / `J — Not symmetric` in
  learning; `F — Left` / `J — Right` in test) turns blue (`#2980b9`); the other label
  dims to grey (`#aaaaaa`). Green (`#2ECC71`) is reserved for correct-answer feedback only.
  Implemented via IDs `cover-label-sym` / `cover-label-notsym`
  (learning) and `twoafc-label-left` / `twoafc-label-right` (test).
- In the test phase, the keydown listener is registered in the **capture phase**
  (`addEventListener(..., true)`) so it fires before jsPsych's bubble-phase handler.

### Timeout feedback (test phase only)
- **Sound**: `Utils.playTimeoutTone()` — descending sweep 440 → 200 Hz over 200 ms,
  triggered in `on_finish` when `data.timed_out === true`.
- No visual change on timeout (the screen transitions automatically).

### Audio latency note
Web Audio API has inherent hardware output latency (typically 20–100 ms depending on
the system). This is a browser/OS limitation and cannot be reduced in code. The lag is
more noticeable with Bluetooth headphones (100–300 ms additional latency); participants
should use wired audio or speakers if they find the feedback distracting.

---

## Breaks Between Blocks
Not included in the current build. Easy to add later as a self-paced screen between
blocks — keep this in mind when structuring the block loop.

---

## Git Tags

Meaningful snapshots are preserved as annotated git tags so earlier designs can be recovered
without keeping backup files in the repo.

| Tag | What it preserves |
|-----|-------------------|
| `counterbalancing-groups-backup` | State before removing group-based counterbalancing. Contains `assignGroup()` / `getTrialsForBlock()` in `utils.js`, group assignment in `consent.html`, group pass-through in `main-task.html`, and the original 9-questions-per-block counterbalancing script. `questionsPerBlock = 9`. |

To inspect a file from a tag: `git show <tag>:experiment/components/utils.js`
To restore the full repo to a tag: `git checkout <tag>`

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
