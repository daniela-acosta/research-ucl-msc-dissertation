"""
show_comments.py
----------------
Reads raw JATOS result folders and prints participant comments
(pre-study from demographics, post-study from debrief) with
participant IDs, Prolific PIDs, start timestamp, and duration.

Usage:
    python data_analysis/scripts/show_comments.py
    python data_analysis/scripts/show_comments.py --results-dir path/to/results
    python data_analysis/scripts/show_comments.py --csv comments.csv
"""

from __future__ import annotations

import argparse
import json
import re
import csv
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT   = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "data" / "results"
PREVIEW_PID = "PREVIEW"

DEBRIEF_FIELDS = [
    "study_purpose_guess",
    "noticed_arrangement",
    "arrangement_description",
    "other_comments",
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _study_id(study_dir: Path) -> str:
    m = re.search(r"(\d+)$", study_dir.name)
    return m.group(1) if m else study_dir.name


def _load_json(path: Path) -> dict | list | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        for line in text.splitlines():
            line = line.strip()
            if line:
                try:
                    obj = json.loads(line)
                    if isinstance(obj, list):
                        return obj
                except json.JSONDecodeError:
                    continue
        return None
    except OSError:
        return None


def _classify(study_dir: Path):
    consent = demographics = trials = debrief = None
    for comp_dir in sorted(study_dir.iterdir()):
        data_file = comp_dir / "data.txt"
        if not data_file.exists():
            continue
        payload = _load_json(data_file)
        if isinstance(payload, list):
            trials = payload
        elif isinstance(payload, dict):
            if "debrief_questions" in payload:
                debrief = payload
            elif "age" in payload:
                demographics = payload
            elif "timestamp" in payload:
                consent = payload
    return consent, demographics, trials, debrief


def _fmt(val: str | None, empty: str = "[none]") -> str:
    if not val or str(val).strip() in ("", "N/A", "n/a", "None", "none", "NA"):
        return empty
    return str(val).strip()


def _duration_str(ms: int | None) -> str:
    if ms is None:
        return "unknown"
    total_s = ms // 1000
    mins, secs = divmod(total_s, 60)
    return f"{mins}m {secs:02d}s"


# ── main ─────────────────────────────────────────────────────────────────────

def load_comments(results_dir: Path) -> list[dict]:
    study_dirs = sorted(
        p for p in results_dir.iterdir()
        if p.is_dir() and p.name.startswith("study_result_")
    )
    if not study_dirs:
        raise FileNotFoundError(f"No study_result_* folders found in {results_dir}")

    rows = []
    for study_dir in study_dirs:
        study_id = _study_id(study_dir)
        consent, demographics, trials, debrief = _classify(study_dir)

        pid = ""
        if consent:
            pid = consent.get("prolific_pid", "")
        elif demographics:
            pid = demographics.get("prolific_pid", "")

        real_pid = pid if (pid and pid != PREVIEW_PID) else ""
        participant_id = real_pid if real_pid else f"local_{study_id}"

        # Timing
        start_ts   = consent.get("timestamp") if consent else None
        start_dt   = None
        if start_ts:
            try:
                start_dt = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Main task duration from last trial's time_elapsed
        main_task_ms = None
        if trials:
            elapsed_vals = [t.get("time_elapsed") for t in trials if t.get("time_elapsed")]
            if elapsed_vals:
                main_task_ms = max(elapsed_vals)

        rows.append({
            "participant_id":        participant_id,
            "prolific_pid":          real_pid,
            "study_result_id":       study_id,
            "start_time":            start_dt.strftime("%Y-%m-%d %H:%M UTC") if start_dt else "unknown",
            "main_task_duration":    _duration_str(main_task_ms),
            "exit_type":             debrief.get("exit_type", "unknown") if debrief else "no debrief",
            # pre-study
            "pre_comments":          _fmt(demographics.get("comments") if demographics else None),
            # post-study
            "study_purpose_guess":   _fmt(debrief["debrief_questions"].get("study_purpose_guess") if debrief else None),
            "noticed_arrangement":   _fmt(debrief["debrief_questions"].get("noticed_arrangement") if debrief else None),
            "arrangement_description": _fmt(debrief["debrief_questions"].get("arrangement_description") if debrief else None),
            "post_comments":         _fmt(debrief["debrief_questions"].get("other_comments") if debrief else None),
        })

    return rows


def print_comments(rows: list[dict]) -> None:
    sep = "═" * 64
    for r in rows:
        print(f"\n{sep}")
        print(f"Participant : {r['participant_id']}")
        print(f"Prolific PID: {r['prolific_pid'] or '[none]'}")
        print(f"Study result: {r['study_result_id']}")
        print(f"Started     : {r['start_time']}")
        print(f"Main task   : {r['main_task_duration']}")
        print(f"Exit        : {r['exit_type']}")
        print()
        print("  PRE-STUDY (demographics):")
        print(f"    comments : {r['pre_comments']}")
        print()
        print("  POST-STUDY (debrief):")
        print(f"    purpose guess        : {r['study_purpose_guess']}")
        print(f"    noticed arrangement  : {r['noticed_arrangement']}")
        print(f"    arrangement described: {r['arrangement_description']}")
        print(f"    other comments       : {r['post_comments']}")
    print(f"\n{sep}")
    print(f"Total: {len(rows)} participant(s)")


def save_csv(rows: list[dict], path: Path) -> None:
    fields = [
        "participant_id", "prolific_pid", "study_result_id",
        "start_time", "main_task_duration", "exit_type",
        "pre_comments",
        "study_purpose_guess", "noticed_arrangement",
        "arrangement_description", "post_comments",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved → {path}")


def main():
    parser = argparse.ArgumentParser(description="Print participant comments from JATOS results.")
    parser.add_argument(
        "--results-dir", "-d",
        type=Path,
        default=RESULTS_DIR,
        help="Path to the results directory (default: data/results/)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        metavar="PATH",
        help="Also save output to a CSV file at this path.",
    )
    args = parser.parse_args()

    rows = load_comments(args.results_dir)
    print_comments(rows)

    if args.csv:
        save_csv(rows, args.csv)


if __name__ == "__main__":
    main()
