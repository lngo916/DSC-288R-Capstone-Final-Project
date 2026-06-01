#!/usr/bin/env bash

# Stop the script immediately if:
# - any command fails (-e)
# - any undefined variable is used (-u)
# - any command inside a pipeline fails (pipefail)
set -euo pipefail

# Folder where rendered HTML notebook reports will be saved.
REPORT_DIR="reports/notebooks"

# Create the report output folder if it does not already exist.
mkdir -p "$REPORT_DIR"

# Find every real Jupyter notebook under notebooks/.
# Skip .ipynb_checkpoints because those are auto-generated backup files
# and should not be included in final reports.
#
# -print0 is used so filenames with spaces or special characters are handled safely.
find notebooks \
  -path "*/.ipynb_checkpoints/*" -prune -o \
  -name "*.ipynb" -print0 |
while IFS= read -r -d '' nb; do
    # Show progress in the terminal.
    echo "Rendering: $nb"

    # Remove the leading "notebooks/" from the notebook path.
    # Example:
    #   notebooks/4_EDA_game.ipynb
    # becomes:
    #   4_EDA_game.ipynb
    rel_path="${nb#notebooks/}"

    # Get the notebook's relative subfolder.
    # If the notebook is directly inside notebooks/, this will be ".".
    rel_dir="$(dirname "$rel_path")"

    # Preserve subfolder structure under reports/notebooks/.
    #
    # Example:
    #   notebooks/eda/example.ipynb
    # becomes:
    #   reports/notebooks/eda/example.html
    #
    # If the notebook is directly inside notebooks/,
    # save the HTML directly under reports/notebooks/.
    if [ "$rel_dir" = "." ]; then
        out_dir="$REPORT_DIR"
    else
        out_dir="$REPORT_DIR/$rel_dir"
    fi

    # Create the output folder for this notebook if needed.
    mkdir -p "$out_dir"

    # Convert the notebook to HTML.
    # The output filename will match the notebook name,
    # but with .html instead of .ipynb.
    jupyter nbconvert \
      --to html \
      "$nb" \
      --output-dir "$out_dir"
done

# Final completion message.
echo "Done rendering notebooks to $REPORT_DIR"
