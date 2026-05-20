# Graph Learning Experiment

Cognitive Science dissertation experiment studying how statistical learning transitions
from implicit to explicit knowledge. Participants are exposed to a sequence of stimuli via
a random walk over a community-structured graph (cover task: symmetry judgement), then
tested on their implicit knowledge of transition probabilities via 2AFC questions.

Supervised by Megan Peters. Built with jsPsych 7 and JATOS.

---

## Repository structure

```
/data/
    counterbalancing_table.csv        — pre-generated trial assignment (source of truth)
    2afc_question_candidates_v2.csv   — full 2AFC question pool with metadata

/experiment/                          — the jsPsych experiment (deploy this folder to JATOS)
    consent.html                      — informed consent; assigns counterbalancing group
    demographics.html                 — age, gender, handedness, language, vision
    instructions.html                 — cover task instructions (symmetry judgement only)
    practice.html                     — 6-step practice with comprehension checks
    main-task.html                    — 4 blocks of learning + 2AFC test
    debrief.html                      — reveals true purpose; redirects to Prolific
    jatos.js                          — local development mock (JATOS replaces this at runtime)
    config.js                         — all tunable parameters (timing, keys, paths, etc.)
    components/
        utils.js                      — shared utilities (walk generation, CSV loading, etc.)
        learning-phase.js             — cover task / random walk trial builder
        test-phase.js                 — 2AFC trial builder
    assets/
        style.css
        stimulus_A.png … stimulus_K.png   — placeholder stimuli (replace with final images)
    data/
        counterbalancing_table.csv    — copy of /data/ version (JATOS can't serve ../data/)
        2afc_question_candidates_v2.csv

/planning/                            — Python scripts (data pipeline, not deployed)
    graph_definition.py               — defines graph, generates question candidates
    counterbalancing.py               — generates counterbalancing_table.csv
    requirements.txt
    venv/

CLAUDE.md                             — full technical context for AI-assisted development
```

**Key design points:**

- All configurable parameters (timing, response keys, block counts, paths) live in `config.js`.
- `jatos.js` in `/experiment/` is a development mock — JATOS serves its own version at runtime.
- CSVs are duplicated into `/experiment/data/` because JATOS can only serve files within the study directory.
- If `/data/counterbalancing_table.csv` is ever regenerated, copy it to `/experiment/data/` too.

---

## Running locally (development)

No JATOS server needed — open any HTML file directly in a browser:

```bash
open experiment/consent.html
```

The mock `jatos.js` stubs the JATOS API and logs all calls to the browser console.
`studySessionData` resets on each page reload, so components don't share state when
testing individually. Group assignment always picks group 1 on a fresh load (expected).

---

## Running with a local JATOS instance

### First-time setup

1. Download JATOS from [https://www.jatos.org/Get-started.html](https://www.jatos.org/Get-started.html) and unzip it.
2. Start the server:

   ```bash
   # Mac / Linux
   cd jatos_VERSION
   ./loader.sh start

   # Windows
   loader.bat start
   ```

3. Open [http://localhost:9000](http://localhost:9000) and log in (default: `admin` / `admin`).

### Stop the server

```bash
./loader.sh stop
```

### Importing the study

1. In the JATOS GUI, go to **Studies → Import Study**.
2. Select the `/experiment/` folder zipped as a `.jzip` file (JATOS's export format), or
   use **New Study** and add each HTML file as a component manually in order:
   `consent → demographics → instructions → practice → main-task → debrief`
3. Click **Run** on the study to test it directly.

### Updating after code changes

Find the study's folder inside the JATOS directory (typically `jatos_VERSION/study_assets/STUDY_NAME/`)
and replace the files there directly. Changes take effect immediately — no re-import needed.

---

## Running on Mindprobe

[Mindprobe](https://www.mindprobe.eu) is a free JATOS hosting service for academic studies.

### One-time account setup

1. Register at [https://www.mindprobe.eu](https://www.mindprobe.eu).
2. Log in — the interface is identical to local JATOS.

### Deploying the study

1. Export the study from your local JATOS instance:
   **Studies → (kebab menu) → Export Study** — saves a `.jzip` file.
2. Log into Mindprobe, go to **Studies → Import Study**, and upload the `.jzip`.
3. The study will appear with all components and assets intact.

### Updating a deployed study

Same export/import cycle as above, or use component-level file replacement in the
Mindprobe GUI for small changes.

### Prolific integration

1. In Mindprobe, open the study → **Worker & Batch Manager** → create a batch →
   **Generate Prolific Link**.
2. Paste that link into Prolific as the study URL.
3. Set the completion redirect in `config.js` (`prolificCompletionURL`) to the
   Prolific completion URL before deploying.

---

## Stimuli

Placeholder images (`stimulus_A.png` … `stimulus_K.png`) are solid-colour squares.
To swap in final stimuli, replace the PNG files in `/experiment/assets/` — no code changes
needed as long as the naming convention (`stimulus_LABEL.png`) is preserved.
