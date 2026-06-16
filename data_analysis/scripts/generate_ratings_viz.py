"""
generate_ratings_viz.py
-----------------------
Reads ratings.csv and generates test_experiment/ratings_viz.html —
a self-contained visual summary showing each fractal image alongside
individual ratings and the mean, sorted by mean rating.

Open ratings_viz.html directly in a browser (no server needed).

Usage:
    python data_analysis/scripts/generate_ratings_viz.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO_ROOT  = Path(__file__).resolve().parents[2]
RATINGS_CSV = REPO_ROOT / "test_experiment" / "results" / "ratings.csv"
OUTPUT_HTML = REPO_ROOT / "test_experiment" / "ratings_viz.html"


def build_stimulus_data(ratings: pd.DataFrame) -> dict[str, list]:
    """Return {'A': [...], 'S': [...]} sorted by mean rating ascending."""
    grouped = (
        ratings.groupby(["stimulus", "stimulus_id", "variant"])["rating"]
        .apply(list)
        .reset_index()
        .rename(columns={"rating": "ratings"})
    )
    # Drop timed-out (NaN) entries before computing mean and passing to JS.
    grouped["ratings"] = grouped["ratings"].apply(lambda r: [x for x in r if pd.notna(x)])
    grouped["mean"] = grouped["ratings"].apply(lambda r: round(pd.Series(r).mean(), 2))
    grouped = grouped.sort_values("mean")

    result = {}
    for variant in ("A", "S"):
        subset = grouped[grouped["variant"] == variant]
        result[variant] = subset[["stimulus", "stimulus_id", "mean", "ratings"]].to_dict("records")

    return result


def render_html(data: dict[str, list]) -> str:
    data_json = json.dumps(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Fractal Symmetry Ratings</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: sans-serif; background: #f5f5f5; padding: 32px; color: #333; }}
    h1 {{ font-size: 1.4rem; margin-bottom: 24px; }}
    h2 {{ font-size: 1.1rem; margin: 32px 0 16px; padding-bottom: 6px;
          border-bottom: 2px solid #ddd; }}
    .grid {{
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .card {{
      background: #fff;
      border-radius: 8px;
      box-shadow: 0 1px 4px rgba(0,0,0,.1);
      padding: 12px;
      width: 180px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }}
    .card img {{
      width: 140px;
      height: 140px;
      object-fit: contain;
    }}
    .card .label {{
      font-size: 0.78rem;
      color: #555;
      text-align: center;
    }}
    .card .mean-val {{
      font-weight: bold;
      font-size: 0.85rem;
    }}
    svg.strip {{ overflow: visible; }}
  </style>
</head>
<body>
  <h1>Fractal symmetry ratings</h1>
  <p style="font-size:0.85rem;color:#888;margin-bottom:8px;">
    Sorted by mean rating (low → high) &nbsp;·&nbsp;
    Dots = individual ratings &nbsp;·&nbsp; ◆ = mean
  </p>

  <div id="root"></div>

  <script>
    const DATA = {data_json};

    const STRIP_W = 156;
    const STRIP_H = 44;
    const PAD     = 14;          // left/right padding inside strip
    const Y_MID   = 22;
    const COLOURS = {{ A: '#e67e22', S: '#2980b9' }};

    function xPos(rating) {{
      // rating 1–5 → pixel x
      return PAD + (rating - 1) / 4 * (STRIP_W - PAD * 2);
    }}

    // Spread dots vertically when they share the same x bucket.
    function yJitter(ratings) {{
      const groups = {{}};
      ratings.forEach((r, i) => {{
        if (!groups[r]) groups[r] = [];
        groups[r].push(i);
      }});
      const jitters = new Array(ratings.length).fill(0);
      Object.values(groups).forEach(indices => {{
        const n = indices.length;
        if (n === 1) return;
        const spread = Math.min((n - 1) * 5, 18);
        indices.forEach((idx, i) => {{
          jitters[idx] = -spread / 2 + (spread / (n - 1)) * i;
        }});
      }});
      return jitters;
    }}

    function makeSVG(ratings, mean, colour) {{
      const jitters = yJitter(ratings);
      const ns = 'http://www.w3.org/2000/svg';

      const svg = document.createElementNS(ns, 'svg');
      svg.setAttribute('class', 'strip');
      svg.setAttribute('width',  STRIP_W);
      svg.setAttribute('height', STRIP_H);

      // Axis line
      const line = document.createElementNS(ns, 'line');
      line.setAttribute('x1', xPos(1)); line.setAttribute('y1', Y_MID);
      line.setAttribute('x2', xPos(5)); line.setAttribute('y2', Y_MID);
      line.setAttribute('stroke', '#ddd'); line.setAttribute('stroke-width', 1.5);
      svg.appendChild(line);

      // Axis tick labels
      [1,2,3,4,5].forEach(v => {{
        const t = document.createElementNS(ns, 'text');
        t.setAttribute('x', xPos(v));
        t.setAttribute('y', STRIP_H - 2);
        t.setAttribute('text-anchor', 'middle');
        t.setAttribute('font-size', '9');
        t.setAttribute('fill', '#aaa');
        t.textContent = v;
        svg.appendChild(t);
      }});

      // Individual rating dots
      ratings.forEach((r, i) => {{
        const cx = xPos(r);
        const cy = Y_MID + jitters[i];
        const circle = document.createElementNS(ns, 'circle');
        circle.setAttribute('cx', cx); circle.setAttribute('cy', cy);
        circle.setAttribute('r', 4);
        circle.setAttribute('fill', colour);
        circle.setAttribute('fill-opacity', 0.45);
        svg.appendChild(circle);
      }});

      // Mean diamond
      const mx = xPos(mean);
      const s  = 6;  // half-size of diamond
      const diamond = document.createElementNS(ns, 'polygon');
      diamond.setAttribute('points',
        `${{mx}},${{Y_MID - s}} ${{mx + s}},${{Y_MID}} ${{mx}},${{Y_MID + s}} ${{mx - s}},${{Y_MID}}`);
      diamond.setAttribute('fill', '#222');
      svg.appendChild(diamond);

      return svg;
    }}

    function renderSection(variant, items, root) {{
      const label = variant === 'A' ? 'Asymmetrical (A)' : 'Symmetrical (S)';
      const colour = COLOURS[variant];

      const h2 = document.createElement('h2');
      h2.textContent = label + ' — sorted by mean rating';
      root.appendChild(h2);

      const grid = document.createElement('div');
      grid.className = 'grid';

      items.forEach(item => {{
        const card = document.createElement('div');
        card.className = 'card';

        const img = document.createElement('img');
        img.src = 'stimuli/' + item.stimulus;
        img.alt = item.stimulus;
        card.appendChild(img);

        const lbl = document.createElement('p');
        lbl.className = 'label';
        lbl.innerHTML = item.stimulus_id +
          '<br><span class="mean-val">mean: ' + item.mean.toFixed(2) + '</span>';
        card.appendChild(lbl);

        card.appendChild(makeSVG(item.ratings, item.mean, colour));
        grid.appendChild(card);
      }});

      root.appendChild(grid);
    }}

    const root = document.getElementById('root');
    renderSection('A', DATA.A, root);
    renderSection('S', DATA.S, root);
  </script>
</body>
</html>
"""


def main():
    ratings = pd.read_csv(RATINGS_CSV)
    data = build_stimulus_data(ratings)
    html = render_html(data)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Saved → {OUTPUT_HTML}")
    print(f"  A stimuli: {len(data['A'])}")
    print(f"  S stimuli: {len(data['S'])}")


if __name__ == "__main__":
    main()
