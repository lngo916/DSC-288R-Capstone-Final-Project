# Steam Reviews — DSC-288R Capstone

Large-scale analysis, modeling, and recommendation on the Steam game-reviews
dataset. The project takes raw reviews through ingestion, health auditing,
exploratory analysis, feature engineering, ML modeling, and a TF-IDF + nearest
-neighbors recommender. - testing here 

---

## 1. Project Overview

We process the Steam reviews corpus with **PySpark**, version the resulting
datasets with **DVC** backed by **AWS S3**, and carry out the analysis through a
sequence of numbered **Jupyter notebooks**. Reusable processing logic lives in a
dedicated source package, configuration is externalized into YAML, and shell
entrypoints automate data retrieval and report rendering.

Two data scales exist:

- **Sampled / subsampled data** — published to S3, runnable from a fresh clone.
- **Full dataset (~50 GB)** — lives on the SDSC Expanse supercomputer and is
  *not* publicly fetchable (see [§9 Important Notes](#9-important-notes--caveats)).

---

## 2. Tech Stack

| Area | Tools |
|------|-------|
| Distributed processing | PySpark |
| Data versioning & storage | DVC + AWS S3 |
| Source dataset | Kaggle (`kagglehub`) |
| Exploratory analysis | ydata-profiling |
| Analysis & reporting | Jupyter, nbconvert |

---

## 3. Architecture — The Layers

The project is organized into logical layers, each mapped to a folder. Three are
active today; two are scaffolded for future development (see
[§11 Future Development](#11-future-development)).

| Layer | Folder | Status | Runs on... | Role |
|-------|--------|--------|------------|------|
| **Data layer** | `data/` | ✅ active | — | DVC-tracked **parquet datasets**. Pulled from S3; version-controlled in git via `.dvc` pointer files. |
| **Logic layer** | `src/` | ✅ active | the data layer | Reusable code — pipelines (`src/pipelines/`) and utilities (`src/utils/`). The **foundation** everything else builds on. |
| **Exploration layer** | `notebooks/` | ✅ active | the logic layer | Numbered Jupyter notebooks — the analysis narrative. Cells are **run manually**. |
| **Automation layer** | `automation/` | 🚧 future | the logic layer | *(Not yet completed.)* Python-script versions of the notebooks that **run the workflow automatically** as SLURM batch jobs — the scripted counterpart to manual notebooks. |
| **Config layer** | `configs/` | 🚧 future | logic, notebooks & automation (cross-cutting) | *(Not yet completed.)* `path.yaml`, `spark.yaml`, `eda.yml`. A **cross-cutting side input** that parameterizes the others (Spark resources, paths, EDA settings). The `ALL_CAPS` constants currently hardcoded in `src/` were meant to live here — see [§11](#11-future-development). Fully wiring this up lets automation run config-driven with no code edits, while notebooks can still override by hand. |
| **Model layer** | `model/` | ✅ active | the logic layer | *(Not yet completed.)* Trained-model **weights and metadata**. Trained via the logic layer, then deployed as a backend service that powers the live site (see [§12](#12-portfolio-website--project-walkthrough)). |
| **Execution layer** | `scripts/` | ✅ active | — | Shell entrypoints: data fetch + notebook rendering. **Operational glue**, not part of the analysis flow. |

Read it bottom-up: each layer *runs on* the one below it (solid arrows). `configs/`
is a **cross-cutting side input** (dashed) that parameterizes logic, notebooks, and
automation alike. `configs/` and `model/` are future; everything is oriented toward
the live site.

```
   ┌─────────────┐
   │  configs/   │ ┄┄┄┄┄┄┄┄┄┄ parameterizes ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄-┐   
   └─────────────┘                                            ┆
                                                              ┆ (Spark, paths,
   ┌─────────────┐        ┌─────────────┐        ┌─────────────┐  EDA, constants)
   │ automation/ │        │ notebooks/  │        │   model/    │  
   │  (SLURM,    │        │  (manual    │        │  weights +  │
   │  scripted)  │        │   cells)    │        │  metadata)  │
   └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
          │                      │                      │ deploys as
          └──────────┬───────────┘                      │ backend service
                     │ all run on                        ▼
                     ▼                            ┌──────────────┐
              ┌─────────────┐                     │  LIVE SITE   │
              │    src/     │  logic layer        │ (portfolio   │
              └──────┬──────┘ ┄┄ configured by ┄┄ │  walkthrough)│
                     │ runs on    configs/        └──────────────┘
                     ▼
              ┌─────────────┐
              │    data/    │  DVC-tracked parquet (pulled from S3)
              └─────────────┘
```

---

## 4. Repository Layout

```
DSC-288R-Capstone-Final-Project/
├── data/                          # Data layer — DVC-tracked parquet (pulled from S3)
│   ├── *.dvc                      #   committed pointer files
│   ├── subsampled_parquet/        #   pulled datasets land here
│   ├── cleaned_sampled_parquet/
│   ├── feature_engineered_sampled_parquet/
│   ├── train_val_test_splits/
│   └── steam_tfidf_nn_recommender_v2.parquet  # TF-IDF + NN recommender artifact
├── models/                        # Model layer — trained Spark ML models (§7)
│   ├── baseline/                  #   default-hyperparameter models
│   │   ├── log_reg/  decision_tree/  random_forest/  xgb/  svm/
│   └── tuned/                     #   hyperparameter-tuned models
│       └── log_reg/  ...
├── src/                           # Logic layer
│   ├── pipelines/                 #   ingest, prep, audit, feature eng, modeling, split
│   └── utils/                     #   io_utils, paths_utils, pyspark_utils
├── notebooks/                     # Exploration layer — numbered analysis notebooks
├── scripts/                       # Execution layer — shell entrypoints
│   ├── fetch_all_dvc_files.sh     #   pull data, images & models from S3 via DVC
│   └── render_all_notebooks.sh    #   render notebooks → HTML reports
├── configs/                       # Config layer (future) — *.yaml
├── docs/                          # DVC workflow notes, roadmaps, pipeline details
├── reports/                       # Generated EDA results & rendered notebook HTML
├── index.html, pages/, ...        # Portfolio website (project walkthrough — §12)
├── .env.reader.example            # AWS reader-credential template (pull)
├── .env.publisher.example         # AWS publisher-credential template (push)
├── requirements.txt               # Python dependencies (§5)
└── README.md
# (planned) automation/            # Python/SLURM batch versions of the notebooks (§11)
```

---

## 5. Prerequisites

- **Python 3.11 recommended** — tested on 3.11; **3.10–3.12** should also work.
  Avoid 3.13 (some dependencies such as `ray`, `numba`, and `ydata-profiling` lag
  on the newest release).
- **git**
- Free disk space for the sampled parquet datasets

> **Don't have Python 3.11?** Get it without touching your system Python:
> - **conda / miniconda:** `conda create -n dsc288r python=3.11 && conda activate dsc288r`
> - **pyenv:** `pyenv install 3.11 && pyenv local 3.11`

> 🐍 **Easiest path — skip all local setup:** open the notebooks in **Google Colab**
> and set `MODE = "COLAB"` in the first cell. Colab ships with Java, libomp, and the
> ML stack preinstalled, so the system dependencies below are handled for you.

### System dependencies (NOT installed by `pip`)

These are **native libraries** `requirements.txt` cannot provide. On macOS, install
both via [Homebrew](https://brew.sh) **before** running the notebooks:

| Dependency | Why | macOS install |
|------------|-----|---------------|
| **JDK 17** | PySpark runs on the JVM. **The version matters** — PySpark 3.5 needs Java 8/11/**17**, PySpark 4.0 needs **17/21**. Java 17 is the safe choice. Too-old (e.g. 15) *or* too-new Java fails with `UnsupportedClassVersionError`. | `brew install openjdk@17` |
| **libomp** | XGBoost's native library needs the OpenMP runtime, or `import xgboost.spark` raises `XGBoostError`. | `brew install libomp` |

After installing JDK 17, point Spark at it (add the exports to `~/.zshrc` to persist):

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
java -version   # should report 17.x
```

> If a notebook still picks up the wrong Java (e.g. VS Code didn't inherit the new
> env), set it in the **first cell, before `create_spark_session`**:
> ```python
> import os
> os.environ["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
> ```
>
> **Linux:** a JDK 17 (`apt install openjdk-17-jdk`) plus `libgomp1` (usually already
> present) are the equivalents.

### Create a virtual environment and install dependencies

So you have every package the notebooks and `src/` modules import — without
guessing — install from the provided [`requirements.txt`](requirements.txt):

```bash
# from the repo root
python3.11 -m venv .venv         # or: python3 -m venv .venv  (if it's a 3.10–3.12)
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

This installs the full stack: PySpark, pandas/numpy/scipy, XGBoost,
ydata-profiling, DVC (`dvc[s3]`), Jupyter, and the rest.

**Register the kernel for Jupyter (only if needed):**

```bash
python -m ipykernel install --user --name dsc288r --display-name "DSC-288R (Python 3.11)"
```

This makes the `.venv` selectable as a kernel in Jupyter, so notebooks run against
the environment where the packages are actually installed. `--user` installs it
into your home dir (no admin needed); `--display-name` is the friendly label shown
in Jupyter's kernel dropdown. **You only need this if you launch Jupyter from
outside the activated venv** (e.g. a system-wide Jupyter or VS Code). If you run
`jupyter lab` *after* `source .venv/bin/activate`, the venv's kernel is already
available and you can skip this. Without the right kernel, notebooks fail with
`ModuleNotFoundError` (e.g. on `import pyspark`).

> **Do this before [§7](#7-data-setup-dvc--s3).** The fetch script uses the **same
> `.venv`**: if it already exists (because you ran the steps above) it **reuses** it,
> otherwise it creates one with just `dvc[s3]`. Running this section first also
> guarantees the venv is built on a **compatible Python (3.10–3.12)** — the script
> itself calls plain `python3 -m venv`, which may resolve to a different version on
> some machines. So there's only ever **one** environment, and no need to create a
> second.

---

## 6. AWS Credentials Setup

**The ready-to-use `.env.reader` is committed in this repo — there's nothing to
create.** Working read-only credentials are already provided so the professor/TA
can fetch the data immediately. (This is intentional; see the
[tradeoff note](#️-a-deliberate-convenience-vs-security-tradeoff) below.)

Files you'll see:

- **`.env.reader`** — *committed and populated.* Read-only keys for *pulling* data.
  **This is all the professor/TA needs.**
- `.env.reader.example` — template, kept for future consistency.
- `.env.publisher.example` — template for *pushing* data (maintainers only).

`.env.reader` contents (already filled in for you):

```
AWS_ACCESS_KEY_ID=AKI...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-west-2
```

### Before you run the fetch script ([§7](#7-data-setup-dvc--s3))

**Clear any AWS credentials already in your shell.** If you have AWS variables
exported from another project or an `aws configure` session, a leftover
`AWS_SESSION_TOKEN` or `AWS_PROFILE` can override the provided reader keys and
cause `403`/auth errors. Reset them in the terminal you'll run the script from:

```bash
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN \
      AWS_PROFILE AWS_DEFAULT_REGION AWS_DEFAULT_PROFILE
```

The fetch script in §7 `source`s `.env.reader` and exports the keys for that run,
so you don't need to export anything yourself.

### ⚠️ A deliberate convenience-vs-security tradeoff

AWS **strongly discourages** sharing sensitive material such as access keys. By
**committing `.env.reader` to this public repo**, I am exposing the reader
credentials **on purpose**, as a deliberate tradeoff: it lets the grader run the
fetch script directly against the data without setting up their own AWS account or
copying keys around — they can be confident the right credentials are already in
place.

I fully understand the implications:

- **GitHub and AWS have both already warned me** about the leaked secret, and AWS
  has **automatically applied a policy that restricts the exposed key** to limit
  blast radius.
- To keep this responsible, **after grading I will deactivate and delete the
  Access Key ID and Secret (key rotation)**, so the exposed credentials are
  permanently invalidated.

This is an intentional, time-boxed decision for grading convenience, and not a
recommended practice. Treat the published keys as throwaway.

---

## 7. Data Setup (DVC + S3)

This is the primary getting-started path. **Data is fetched from S3, but version
control lives in `data/` via DVC**. The `.dvc` pointer files are committed to
git, and the actual parquet is pulled on demand.

> 📋 **Do [§5](#5-prerequisites) first.** The script reuses the `.venv` you created
> there (building it on Python 3.11). If you skip §5, the script will create its own
> `.venv` with just `dvc[s3]` — enough to pull data, but you'll still need the §5
> install before running the notebooks.

1. **Grant execute permission on the fetch script** (required):
   ```bash
   chmod +x scripts/fetch_all_dvc_files.sh
   ```
2. **Run the fetch script from the repo root:**
   ```bash
   bash scripts/fetch_all_dvc_files.sh
   ```

What the script does: validates the repo, builds a Python virtual environment,
installs `dvc[s3]`, loads your reader credentials, and runs `dvc pull` for the
data, images, and models against the `s3_sample`, `s3_images`, and `s3_models`
remotes respectively.

**DVC remotes** (from `.dvc/config`):

| Remote | URL | Use |
|--------|-----|-----|
| `s3_sample` *(default)* | `s3://dsc-288r-capstone-steam-review-sampled-data/dvcstore` | Pull sampled data from S3 |
| `s3_images` | `s3://dsc-288r-capstone-steam-review-sampled-data/dvcstore/imagestore` | Pull images from S3 |
| `s3_models` | `s3://dsc-288r-capstone-steam-review-sampled-data/dvcstore/modelstore` | Pull models from S3 |
| `local_sample` | `../dvcstore` | Local fallback store |

After the pull, the datasets land in `data/`:
`subsampled_parquet/`, `cleaned_sampled_parquet/`,
`feature_engineered_sampled_parquet/`, `train_val_test_splits/` and `steam_tfidf_nn_recommender_v2.parquet`.
Images land in `images/` and models in `models/`.

⏱️ **The fetch completes in under ~17 minutes.** After that, open Jupyter and run
the notebooks.

---

## 8. Notebook Pipeline Map

Notebooks are **run manually in Jupyter, in numeric order** — there are no
automated run commands. After fetching the sampled data, you are free to run
**notebook 3 and onward**, since those operate on the sampled/subsampled data
that is present locally.

| Notebook | Purpose | Runnable from clone? |
|----------|---------|----------------------|
| `0_RECOMMENDER_TF_IDF+NNBRUTE_Steam_playground.ipynb` | TF-IDF + NN recommender | ✅ |
| `1_data_ingestion.ipynb` | Download / ingest raw Steam reviews | ❌ needs full dataset |
| `2_data_subsampling.ipynb` | Create sampled subsets | ❌ needs full dataset |
| `3_data_health_audit_&_prep_sample.ipynb` | Health audit + prep (sample) | ✅ |
| `3_data_health_audit_&_prep_full.ipynb` | Health audit + prep (full) | ❌ needs full dataset |
| `4_EDA_game.ipynb` | Game-data EDA | ✅ |
| `4_EDA_review_sample.ipynb` | Review EDA (sample) | ✅ |
| `4_EDA_review_full.ipynb` | Review EDA (full) | ❌ needs full dataset |
| `5_feature_engineering.ipynb` | Feature engineering | ✅ |
| `6_train_test_split.ipynb` | Train / val / test split | ✅ |
| `7_ML_modeling.ipynb` | ML model training | ✅ |
| `8_ML_tuning.ipynb` | ML fine tuning| ✅ |


> **Note:** The full-dataset notebooks (`*_full`, plus ingestion and subsampling)
> are included for reproducibility documentation but will not run without the
> Expanse data — see below.

---

## 9. Important Notes / Caveats

- The first **~50 GB / full dataset** lives on the **SDSC Expanse Supercomputer —
  Lustre scratch (temporary) storage**, which is **not yet connected to S3**.
- Therefore only the **sampled** data is published to S3, and only the
  sampled/subsampled notebooks (**3 and onward**) are runnable from a fresh clone.
- Full-dataset notebooks are retained for completeness and to document the
  end-to-end pipeline, but require the Expanse data to execute.

---

## 10. Docs & Reports

- **DVC architecture / workflow:** [`docs/dvc_workflow.md`](docs/dvc_workflow.md)
- **Pipeline details:** `docs/review_data_pipeline_details.pdf`
- **Project roadmaps:** `docs/project_roadmap_*.png`
- **Rendered results (no execution required):** browse the HTML in
  `reports/notebooks/` to read the analysis without running anything. Regenerate
  them with:
  ```bash
  bash scripts/render_all_notebooks.sh
  ```

---

## 11. Future Development

This project is built to scale beyond the grading snapshot. Planned and in-progress
work:

- **`automation/` layer (SLURM batch jobs).** Convert each analysis notebook into a
  standalone Python script that imports from `src/`, so the full pipeline can be
  submitted as **SLURM jobs** on a cluster (e.g. SDSC Expanse) and run end-to-end
  without manual notebook execution. This is the planned counterpart to the
  `notebooks/` exploration layer.
- **Activate the `configs/` layer (imperative → declarative).** The YAML configs
  (`path.yaml`, `spark.yaml`, `eda.yml`) exist but aren't fully wired in. The
  `ALL_CAPS` constants currently hardcoded across `src/` were **prepared to be
  externalized into config** (YAML/TOML) — under time constraint they were left
  **imperative (hardcoded) instead of declarative**. Lifting them into `configs/`
  makes the workflow reconfigurable with **no code changes**, parameterizing logic,
  notebooks, and automation alike.
- **`model/` layer + live deployment.** expose `model/`  as
  a **backend service** that powers the **live site** — turning the portfolio
  walkthrough into an interactive, model-backed demo.
- **Connect the full dataset to S3.** Wire the ~50 GB full dataset on SDSC Expanse
  Lustre scratch into the DVC/S3 remote so the full-scale notebooks become
  reproducible for everyone (currently gated by storage/cost — see
  [§9](#9-important-notes--caveats)).
- **Reproducibility hardening.** Pin dependency versions, add a `dvc.yaml` pipeline
  to formalize stage dependencies, and explore containerization (Docker) for a
  one-command environment.
- **Model & recommender expansion.** Iterate beyond the TF-IDF + nearest-neighbors
  baseline toward richer retention models and ranking/recommendation approaches.

---

## 12. Portfolio Website — Project Walkthrough

This repo ships a **portfolio-level, presentation-style walkthrough** of the entire
project as a small static website — a guided tour of the problem, the data
pipeline, the modeling, and the team.

- **`index.html`** — *"Steam: Player Retention"* landing / presentation, including
  **feature-level behavioral insights**, **model exploration**, and a **Meet the
  Team** section.
- **`pages/pipeline.html`** — the data-pipeline story.
- **`pages/ml.html`** — the machine-learning walkthrough.
- **`thankyou.html`** — closing page.

Open `index.html` in a browser to explore it **locally** — this always works
straight from the repo, no setup required.

> **Hosted version (tentative).** A publicly hosted build (e.g. via **GitHub
> Pages**) *may or may not* be released, depending on time and whether the
> model-backed backend ([§11](#11-future-development)) lands. The static
> walkthrough is fully usable locally regardless. If a live version ships, the URL
> will be added here.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Permission denied` on fetch script | `chmod +x scripts/fetch_all_dvc_files.sh` |
| Missing-credentials error | Confirm `.env.reader` exists and is populated |
| `dvc pull` auth / 403 errors | Clear stale AWS env vars (`unset AWS_SESSION_TOKEN AWS_PROFILE …`, see [§6](#6-aws-credentials-setup) step 1), then verify the reader keys and `AWS_DEFAULT_REGION` (note: keys are rotated after grading) |
| `ModuleNotFoundError` in a notebook, but `pip show <pkg>` finds it | The notebook kernel isn't your `.venv`. In VS Code, use the **kernel picker (top-right)** → select `./.venv/bin/python`. Verify with `import sys; print(sys.executable)`. |
| `ModuleNotFoundError` (package genuinely missing) | Activate the venv and `pip install -r requirements.txt` (see [§5](#5-prerequisites)) |
| `XGBoostError` on `import xgboost.spark` (mentions OpenMP / "32-bit Python") | Install the OpenMP runtime: `brew install libomp`, then **restart the kernel**. The "32-bit Python" line is a red herring. (see [§5](#5-prerequisites)) |
| Spark: `UnsupportedClassVersionError` / `class file version 61.0` | Wrong Java version. Install **JDK 17** (`brew install openjdk@17`) and set `JAVA_HOME` (see [§5](#5-prerequisites)). "61.0" = Java 17 required; a lower "recognized up to" number = your Java is too old. |
| Spark: `JAVA_GATEWAY_EXITED` (gateway exited before sending its port) | The JVM launched but died. Two causes: **(a)** wrong/old Java → fix per the row above (JDK 17 + `JAVA_HOME`); **(b)** the default Spark config requests **10g driver memory**, too big for a laptop → run in local mode with less memory (next row). |
| Spark too big for a laptop (cluster-sized config) | The default `SPARK_CONFIGS` are sized for the Expanse cluster. For local runs, override at the call site: `create_spark_session(app_name, extra_configs={"spark.driver.memory": "4g", "spark.master": "local[*]"})`. |
| Spark fails to start / `JAVA_HOME` errors | Confirm `java -version` reports **17.x** and `JAVA_HOME` points at JDK 17 (see [§5](#5-prerequisites)) |
| Notebook can't find data (`FileNotFoundException` on a parquet path) | Set `MODE = "LOCAL"` in the notebook's first cell, and ensure the data was pulled into `data/` (see [§7](#7-data-setup-dvc--s3)). Paths resolve to `<repo>/data/...` via `ProjectPaths`. |
