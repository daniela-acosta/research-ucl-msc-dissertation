#!/usr/bin/env bash
# Run the full analysis pipeline on data/to_review/ without touching data/results/.
# Outputs (CSVs + plots) are written back into data/to_review/.
#
# Usage:
#   bash data_analysis/scripts/run_review.sh           (from repo root)
#   bash run_review.sh                                 (from this directory)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REVIEW_DIR="$REPO_ROOT/data/to_review"

echo "=== Review pipeline ==="
echo "Data dir : $REVIEW_DIR"
echo ""

# 1. Load raw JATOS results into combined_raw.csv
echo "--- Step 1: load_data.py ---"
python "$SCRIPT_DIR/load_data.py" \
  --results-dir     "$REVIEW_DIR" \
  --output          "$REVIEW_DIR/combined_raw.csv" \
  --demographics-out "$REVIEW_DIR/demographics.csv"

echo ""

# 2. Preprocess into test_trials.csv + learning_trials.csv
echo "--- Step 2: preprocess.py ---"
python "$SCRIPT_DIR/preprocess.py" \
  --input       "$REVIEW_DIR/combined_raw.csv" \
  --test-out    "$REVIEW_DIR/test_trials.csv" \
  --learning-out "$REVIEW_DIR/learning_trials.csv"

echo ""

# 3. Generate exploratory plots (written to data/to_review/)
echo "--- Step 3: exploration.py ---"
python "$SCRIPT_DIR/exploration.py" \
  --data-dir "$REVIEW_DIR"

echo ""
echo "=== Done. Outputs in $REVIEW_DIR ==="
