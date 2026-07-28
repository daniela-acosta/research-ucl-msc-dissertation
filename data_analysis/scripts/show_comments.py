"""
show_comments.py
----------------
Reads raw JATOS result folders and generates an HTML report of participant
comments (pre-study from demographics, post-study from debrief) with
participant IDs, Prolific PIDs, start timestamps, and main-task duration.

Usage:
    python data_analysis/scripts/show_comments.py --results-dir ../data/to_review
    python data_analysis/scripts/show_comments.py --results-dir ../data/to_review --open
    python data_analysis/scripts/show_comments.py --results-dir ../data/to_review --csv comments.csv
"""

from __future__ import annotations

import argparse
import csv
import html as _html
import json
import re
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "data" / "results"
PREVIEW_PID = "PREVIEW"


# ── data loading ─────────────────────────────────────────────────────────────

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


def _fmt(val, empty="—") -> str:
    if not val or str(val).strip() in ("", "N/A", "n/a", "None", "none", "NA"):
        return empty
    return str(val).strip()


def _duration_str(ms: int | None) -> str:
    if ms is None:
        return "—"
    total_s = ms // 1000
    mins, secs = divmod(total_s, 60)
    return f"{mins}m {secs:02d}s"


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

        start_ts = consent.get("timestamp") if consent else None
        start_dt = None
        if start_ts:
            try:
                start_dt = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
            except ValueError:
                pass

        main_task_ms = None
        if trials:
            elapsed_vals = [t.get("time_elapsed") for t in trials if t.get("time_elapsed")]
            if elapsed_vals:
                main_task_ms = max(elapsed_vals)

        dq = debrief["debrief_questions"] if debrief else {}
        rows.append({
            "participant_id":          participant_id,
            "prolific_pid":            real_pid,
            "study_result_id":         study_id,
            "start_time":              start_dt.strftime("%b %d, %Y · %H:%M UTC") if start_dt else "—",
            "main_task_duration":      _duration_str(main_task_ms),
            "exit_type":               debrief.get("exit_type", "unknown") if debrief else "no debrief",
            "pre_comments":            _fmt(demographics.get("comments") if demographics else None),
            "study_purpose_guess":     _fmt(dq.get("study_purpose_guess")),
            "noticed_arrangement":     _fmt(dq.get("noticed_arrangement")),
            "arrangement_description": _fmt(dq.get("arrangement_description")),
            "post_comments":           _fmt(dq.get("other_comments")),
        })

    return rows


# ── HTML generation ───────────────────────────────────────────────────────────

_CSS = """
:root {
  --bg:           #F0F2F5;
  --card:         #FFFFFF;
  --border:       #DDE1E9;
  --text:         #111827;
  --text-2:       #6B7280;
  --accent:       #3B5BDB;
  --pre-color:    #0D9488;
  --post-color:   #7C3AED;
  --ok-bg:        #DCFCE7; --ok-fg:   #166534;
  --warn-bg:      #FEF3C7; --warn-fg: #92400E;
  --neu-bg:       #F3F4F6; --neu-fg:  #374151;
  --mono: 'SF Mono', 'Fira Code', 'Cascadia Code', ui-monospace, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg:     #0F1117; --card:   #1A1D24; --border: #2C303A;
    --text:   #F1F3F8; --text-2: #8B95A8;
    --ok-bg:  #14532D; --ok-fg:  #86EFAC;
    --warn-bg:#78350F; --warn-fg:#FCD34D;
    --neu-bg: #1F2937; --neu-fg: #D1D5DB;
  }
}
:root[data-theme="dark"] {
  --bg:     #0F1117; --card:   #1A1D24; --border: #2C303A;
  --text:   #F1F3F8; --text-2: #8B95A8;
  --ok-bg:  #14532D; --ok-fg:  #86EFAC;
  --warn-bg:#78350F; --warn-fg:#FCD34D;
  --neu-bg: #1F2937; --neu-fg: #D1D5DB;
}
:root[data-theme="light"] {
  --bg: #F0F2F5; --card: #FFFFFF; --border: #DDE1E9;
  --text: #111827; --text-2: #6B7280;
  --ok-bg: #DCFCE7; --ok-fg: #166534;
  --warn-bg: #FEF3C7; --warn-fg: #92400E;
  --neu-bg: #F3F4F6; --neu-fg: #374151;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  line-height: 1.6;
}
.page { max-width: 1100px; margin: 0 auto; padding: 40px 32px 80px; }

/* ── page header ── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-bottom: 18px;
  border-bottom: 2px solid var(--accent);
  margin-bottom: 36px;
  flex-wrap: wrap;
  gap: 8px;
}
.page-header h1 {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 26px;
  font-weight: normal;
  letter-spacing: -0.3px;
}
.page-meta { font-size: 12.5px; color: var(--text-2); }

/* ── section headings ── */
.section-heading {
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--text-2);
  margin-bottom: 14px;
}

/* ── summary table ── */
.summary-section { margin-bottom: 48px; }
.table-scroll { overflow-x: auto; }
.summary-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  font-variant-numeric: tabular-nums;
}
.summary-table th {
  text-align: left;
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-2);
  padding: 7px 14px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.summary-table td {
  padding: 8px 14px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
.summary-table td.wrap { max-width: 200px; word-break: break-word; }
.summary-table tr:last-child td { border-bottom: none; }
.summary-table tbody tr:hover td { background: color-mix(in srgb, var(--accent) 5%, var(--card)); }

/* ── cards ── */
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: 20px;
  overflow: hidden;
}
.card-header {
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.p-num {
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-2);
}
.p-id {
  font-family: var(--mono);
  font-size: 12.5px;
  font-weight: 600;
}
.card-meta {
  display: flex;
  flex-wrap: wrap;
  column-gap: 20px;
  row-gap: 2px;
  font-size: 12.5px;
  color: var(--text-2);
}
.card-meta b { color: var(--text); font-weight: 500; }
.card-meta .mono { font-family: var(--mono); font-size: 11.5px; }
.card-body {
  display: grid;
  grid-template-columns: 1fr 2fr;
}
.card-section { padding: 16px 20px; }
.card-section + .card-section { border-left: 1px solid var(--border); }
.card-section-title {
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  margin-bottom: 12px;
}
.pre .card-section-title  { color: var(--pre-color); }
.post .card-section-title { color: var(--post-color); }
.field { margin-bottom: 12px; }
.field:last-child { margin-bottom: 0; }
.field-label {
  display: block;
  font-size: 10.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-2);
  margin-bottom: 2px;
}
.field-value { font-size: 13.5px; color: var(--text); line-height: 1.55; }
.empty { color: var(--text-2); font-style: italic; font-size: 13px; }

/* ── badges ── */
.badge {
  display: inline-block;
  font-size: 10.5px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 3px;
  text-transform: capitalize;
  letter-spacing: 0.02em;
}
.badge-ok   { background: var(--ok-bg);   color: var(--ok-fg); }
.badge-warn { background: var(--warn-bg); color: var(--warn-fg); }
.badge-neu  { background: var(--neu-bg);  color: var(--neu-fg); }
.mono { font-family: var(--mono); font-size: 12px; }

/* ── print ── */
@media print {
  body { background: white; }
  .summary-section, .page-meta { display: none; }
  .card { page-break-inside: avoid; border: 1px solid #ccc; }
  .page { padding: 0; }
}
"""

def _esc(v) -> str:
    return _html.escape(str(v)) if v else ""


def _badge(exit_type: str) -> str:
    if exit_type == "completed":
        return '<span class="badge badge-ok">Completed</span>'
    if exit_type == "no debrief":
        return '<span class="badge badge-warn">No debrief</span>'
    return f'<span class="badge badge-neu">{_esc(exit_type)}</span>'


def _trunc(text: str, n: int = 55) -> str:
    if text == "—":
        return '<span class="empty">—</span>'
    escaped = _esc(text)
    return escaped[:n] + ("…" if len(text) > n else "")


def _field(label: str, value: str) -> str:
    val_html = (
        '<span class="empty">—</span>'
        if value == "—"
        else f'<p class="field-value">{_esc(value)}</p>'
    )
    return f'<div class="field"><span class="field-label">{label}</span>{val_html}</div>'


def generate_html(rows: list[dict]) -> str:
    now = datetime.now(timezone.utc).strftime("%b %d, %Y · %H:%M UTC")
    n = len(rows)

    # summary table
    trs = []
    for i, r in enumerate(rows, 1):
        pid_short = r["participant_id"][:20] + ("…" if len(r["participant_id"]) > 20 else "")
        ppid_short = (r["prolific_pid"][:20] + "…") if r["prolific_pid"] else "—"
        trs.append(
            f"<tr>"
            f'<td class="mono">{i}</td>'
            f'<td class="mono">{_esc(pid_short)}</td>'
            f'<td class="mono">{_esc(ppid_short)}</td>'
            f"<td>{_esc(r['start_time'])}</td>"
            f"<td>{_esc(r['main_task_duration'])}</td>"
            f"<td>{_badge(r['exit_type'])}</td>"
            f'<td class="wrap">{_trunc(r["pre_comments"])}</td>'
            f'<td class="wrap">{_trunc(r["study_purpose_guess"])}</td>'
            f'<td class="wrap">{_trunc(r["post_comments"])}</td>'
            f"</tr>"
        )

    # participant cards
    cards = []
    for i, r in enumerate(rows, 1):
        pid_disp = r["participant_id"][:32] + ("…" if len(r["participant_id"]) > 32 else "")
        cards.append(
            f'<article class="card" id="p{i}">'
            f'<div class="card-header">'
            f'<div class="card-title">'
            f'<span class="p-num">#{i}</span>'
            f'<span class="p-id">{_esc(pid_disp)}</span>'
            f'{_badge(r["exit_type"])}'
            f"</div>"
            f'<div class="card-meta">'
            f'<span><b>Prolific</b> <span class="mono">{_esc(r["prolific_pid"] or "—")}</span></span>'
            f'<span><b>Study result</b> <span class="mono">{_esc(r["study_result_id"])}</span></span>'
            f'<span><b>Started</b> {_esc(r["start_time"])}</span>'
            f'<span><b>Main task</b> {_esc(r["main_task_duration"])}</span>'
            f"</div>"
            f"</div>"
            f'<div class="card-body">'
            f'<div class="card-section pre">'
            f'<p class="card-section-title">Pre-study</p>'
            f'{_field("Comments", r["pre_comments"])}'
            f"</div>"
            f'<div class="card-section post">'
            f'<p class="card-section-title">Post-study · debrief</p>'
            f'{_field("Study purpose guess", r["study_purpose_guess"])}'
            f'{_field("Noticed arrangement", r["noticed_arrangement"])}'
            f'{_field("Arrangement described as", r["arrangement_description"])}'
            f'{_field("Other comments", r["post_comments"])}'
            f"</div>"
            f"</div>"
            f"</article>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Participant Comments</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
  <header class="page-header">
    <h1>Participant Comments</h1>
    <p class="page-meta">Generated {now} &nbsp;·&nbsp; {n} participant{"s" if n != 1 else ""}</p>
  </header>

  <section class="summary-section">
    <p class="section-heading">Summary</p>
    <div class="table-scroll">
      <table class="summary-table">
        <thead><tr>
          <th>#</th><th>Participant ID</th><th>Prolific PID</th>
          <th>Started</th><th>Duration</th><th>Exit</th>
          <th>Pre-study</th><th>Purpose guess</th><th>Other comments</th>
        </tr></thead>
        <tbody>{"".join(trs)}</tbody>
      </table>
    </div>
  </section>

  <section>
    <p class="section-heading">Full responses</p>
    {"".join(cards)}
  </section>
</div>
</body>
</html>"""


# ── CSV output ────────────────────────────────────────────────────────────────

def save_csv(rows: list[dict], path: Path) -> None:
    fields = [
        "participant_id", "prolific_pid", "study_result_id",
        "start_time", "main_task_duration", "exit_type",
        "pre_comments", "study_purpose_guess", "noticed_arrangement",
        "arrangement_description", "post_comments",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved CSV  → {path}")


def save_coding_csv(rows: list[dict], path: Path) -> None:
    """Slim CSV for topic coding: participant_id + comment columns only, empty string for blanks."""
    fields = [
        "participant_id",
        "pre_comments",
        "study_purpose_guess",
        "noticed_arrangement",
        "arrangement_description",
        "post_comments",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) == "—" else row.get(k, "")) for k in fields})
    print(f"Saved coding CSV → {path}")


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate a participant comments report.")
    parser.add_argument(
        "--results-dir", "-d",
        type=Path,
        default=RESULTS_DIR,
        help="Path to the results directory (default: data/results/)",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=None,
        metavar="PATH",
        help="Output HTML path (default: <results-dir>/comments.html)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        metavar="PATH",
        help="Also save a full CSV at this path.",
    )
    parser.add_argument(
        "--coding-csv",
        type=Path,
        default=None,
        metavar="PATH",
        help="Save a slim coding CSV (participant_id + comment columns only). "
             "Default: <results-dir>/comments_coding.csv",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the HTML report in the default browser after saving.",
    )
    args = parser.parse_args()

    rows = load_comments(args.results_dir)

    html_path = args.html or (args.results_dir / "comments.html")
    html_path.write_text(generate_html(rows), encoding="utf-8")
    print(f"Saved HTML → {html_path}")

    if args.csv:
        save_csv(rows, args.csv)

    coding_path = args.coding_csv or (args.results_dir / "comments_coding.csv")
    save_coding_csv(rows, coding_path)

    if args.open:
        webbrowser.open(html_path.resolve().as_uri())


if __name__ == "__main__":
    main()
