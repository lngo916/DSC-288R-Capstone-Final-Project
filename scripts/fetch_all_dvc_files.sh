#!/usr/bin/env bash

set -euo pipefail

# ============================================================
# Setup + pull all DVC-tracked files (data, images, models)
# from the project's S3 remotes.
#
# Run from the repo root:
#   bash scripts/fetch_all_dvc_files.sh
#
# Required local file, NOT committed to GitHub:
#   .env.reader
# ============================================================

PROJECT_ROOT="$(pwd)"
VENV_DIR=".venv"
ENV_FILE=".env.reader"

# Each entry is "<dvc_file> <remote>". Data lives in s3_sample,
# images in s3_images, models in s3_models. All three remotes
# resolve under the dvcstore/ prefix, so the reader keys cover them.
PULL_TARGETS=(
  "data/cleaned_sampled_parquet.dvc s3_sample"
  "data/feature_engineered_sampled_parquet.dvc s3_sample"
  "data/subsampled_parquet.dvc s3_sample"
  "data/train_val_test_splits.dvc s3_sample"
  "data/steam_tfidf_nn_recommender_v2.parquet.dvc s3_sample"
  "images.dvc s3_images"
  "models.dvc s3_models"
)

# Distinct remotes referenced above (used for the remote-config check).
DVC_REMOTES=("s3_sample" "s3_images" "s3_models")

echo "Project root: ${PROJECT_ROOT}"

# ------------------------------------------------------------
# 1. Check that we are in a Git/DVC repo
# ------------------------------------------------------------

if [ ! -d ".git" ]; then
  echo "ERROR: This does not look like the repo root. Missing .git/"
  echo "Please cd into DSC-288R-Capstone-Final-Project first."
  exit 1
fi

if [ ! -d ".dvc" ]; then
  echo "ERROR: This does not look like a DVC repo. Missing .dvc/"
  echo "Make sure the repo contains DVC metadata."
  exit 1
fi

# ------------------------------------------------------------
# 2. Check .env.reader exists
# ------------------------------------------------------------

if [ ! -f "${ENV_FILE}" ]; then
  echo "ERROR: Missing ${ENV_FILE}"
  echo
  echo "Create ${ENV_FILE} in the repo root with:"
  echo
  echo "AWS_ACCESS_KEY_ID=your_reader_access_key_id"
  echo "AWS_SECRET_ACCESS_KEY=your_reader_secret_access_key"
  echo "AWS_DEFAULT_REGION=your_bucket_region"
  echo
  echo "Do NOT commit ${ENV_FILE} to GitHub."
  exit 1
fi

# ------------------------------------------------------------
# 3. Create Python virtual environment
# ------------------------------------------------------------

if [ ! -d "${VENV_DIR}" ]; then
  echo "Creating Python virtual environment: ${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"
else
  echo "Virtual environment already exists: ${VENV_DIR}"
fi

# ------------------------------------------------------------
# 4. Activate virtual environment
# ------------------------------------------------------------

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "Using Python:"
python --version

# ------------------------------------------------------------
# 5. Install DVC with S3 support
# ------------------------------------------------------------

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing DVC with S3 support..."
python -m pip install --upgrade "dvc[s3]"

echo "Checking DVC installation..."
dvc --version

# ------------------------------------------------------------
# 6. Load reader credentials
# ------------------------------------------------------------

echo "Loading AWS reader credentials from ${ENV_FILE}"

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [ -z "${AWS_ACCESS_KEY_ID:-}" ]; then
  echo "ERROR: AWS_ACCESS_KEY_ID is missing from ${ENV_FILE}"
  exit 1
fi

if [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
  echo "ERROR: AWS_SECRET_ACCESS_KEY is missing from ${ENV_FILE}"
  exit 1
fi

if [ -z "${AWS_DEFAULT_REGION:-}" ]; then
  echo "ERROR: AWS_DEFAULT_REGION is missing from ${ENV_FILE}"
  exit 1
fi

echo "AWS_ACCESS_KEY_ID loaded: ${AWS_ACCESS_KEY_ID:0:4}********"
echo "AWS_DEFAULT_REGION loaded: ${AWS_DEFAULT_REGION}"

# ------------------------------------------------------------
# 7. Check DVC remotes
# ------------------------------------------------------------

echo "Configured DVC remotes:"
dvc remote list

for remote in "${DVC_REMOTES[@]}"; do
  if ! dvc remote list | grep -q "^${remote}[[:space:]]"; then
    echo "ERROR: DVC remote '${remote}' is not configured."
    echo "Expected remote name: ${remote}"
    echo "Ask the project owner to commit .dvc/config with the S3 remotes."
    exit 1
  fi
done

# ------------------------------------------------------------
# 8. Check that requested .dvc files exist
# ------------------------------------------------------------

echo "Checking requested DVC metadata files..."

missing_files=0

for target in "${PULL_TARGETS[@]}"; do
  dvc_file="${target%% *}"
  if [ ! -f "${dvc_file}" ]; then
    echo "MISSING: ${dvc_file}"
    missing_files=1
  else
    echo "FOUND:   ${dvc_file}"
  fi
done

if [ "${missing_files}" -ne 0 ]; then
  echo
  echo "ERROR: One or more .dvc files are missing."
  echo "Check whether the file names in this script match the repo."
  echo
  echo "Helpful command:"
  echo "  find . -name '*.dvc' | sort"
  exit 1
fi

# ------------------------------------------------------------
# 9. Pull selected DVC-tracked files
# ------------------------------------------------------------

echo
echo "Pulling selected DVC files from their remotes"
echo

# Force to overwrite existing local DVC-tracked data folders.
FORCE_PULL="${FORCE_PULL:-false}"

for target in "${PULL_TARGETS[@]}"; do
  dvc_file="${target%% *}"
  remote="${target##* }"
  echo "Pulling ${dvc_file} (remote: ${remote}) ..."

  if [ "${FORCE_PULL}" = "true" ]; then
    dvc pull "${dvc_file}" -r "${remote}" -j 1 --force
  else
    dvc pull "${dvc_file}" -r "${remote}" -j 1
  fi
done

# ------------------------------------------------------------
# 10. Final status
# ------------------------------------------------------------

echo
echo "DVC pull completed."
echo
echo "Pulled data status:"
for target in "${PULL_TARGETS[@]}"; do
  dvc_file="${target%% *}"
  remote="${target##* }"
  echo
  echo "Status for ${dvc_file} (remote: ${remote}):"
  dvc status -r "${remote}" "${dvc_file}" || true
done

echo
echo "Done."
