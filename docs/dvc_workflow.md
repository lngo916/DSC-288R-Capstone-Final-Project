# 1. Your Physical Setup
```text
┌──────────────────────────────────────────────────────────────┐
│ GitHub Repo & Expanse $HOME: project repo                    |  
|                                                              |
│ /home/bguo3/bguo3/DSC-288R-Capstone-Final-Project (Expanse)  |
│                                                              │
│ Stores small text metadata only:                             │
│   - source code                                              │
│   - notebooks                                                │
│   - .dvc/config                                              │
│   - .dvcignore                                               │
│   - data/*.dvc                                               │
│   - dvc.yaml / dvc.lock later                                │
│                                                              │
│ Does NOT store real CSV / Parquet data                       │
└──────────────────────────────────────────────────────────────┘
                            ▲
                            │ git push / git pull
                            │
┌──────────────────────────────────────────────────────────────┐
│ Expanse Lustre: real data storage                            │
│                                                              │
│ /expanse/lustre/scratch/bguo3/temp_project/steam_review/     |
│                                                              │
│ ├── raw_csv/                                                 │
│ ├── full_parquet/                                            │
│ ├── cleaned_parquet/                                         │
│ ├── feature_engineered_parquet/                              │
│ ├── subsampled_parquet/                                      │
│ ├── train_val_test_splits/                                   │
│ └── game_KNN.parquet/                                        │
│                                                              │
│ This is where the actual large data lives                    │
└──────────────────────────────────────────────────────────────┘
```

# 2. Add the DVC cache component
When you run
```bash
dvc cache dir /expanse/lustre/scratch/bguo3/temp_project/dvc_cache/steam_review_project
```

```text
┌──────────────────────────────────────────────────────────────┐
│ Expanse $HOME repo                                           │
│                                                              │
│ data/cleaned_parquet  ──► real Parquet directory             │
│                                                              │
│ data/cleaned_parquet.dvc                                     │
│   = small DVC pointer file                                   │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               │ dvc add data/cleaned_parquet
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ DVC Cache on Lustre                                          │
│                                                              │
│ /expanse/lustre/scratch/bguo3/temp_project/dvc_cache/...     │
│                                                              │
│ Stores content-addressed copies/hashes of tracked data       │
│                                                              │
│ Example idea:                                                │
│   hash_AAA → part-00000.parquet                              │
│   hash_BBB → part-00001.parquet                              │
│   hash_DIR → directory listing of cleaned_parquet            │
└──────────────────────────────────────────────────────────────┘
```

# 3. Add New Data Content
Original Data
```text
Snapshot: cleaned_parquet version A

data/cleaned_parquet/
├── part-00000.parquet
├── part-00001.parquet
└── _SUCCESS
```

When you run
```bash
dvc add data/cleaned_parquet
```

```text
┌──────────────────────────────┐
│ data/cleaned_parquet/        │
│ real Spark Parquet directory │
└──────────────┬───────────────┘
               │ read files + compute hashes
               ▼
┌──────────────────────────────┐
│ DVC cache                    │
│ stores hashed data objects   │
└──────────────┬───────────────┘
               │ writes pointer metadata
               ▼
┌──────────────────────────────┐
│ data/cleaned_parquet.dvc     │
│ small text metadata file     │
└──────────────┬───────────────┘
               │ commit pointer
               ▼
┌──────────────────────────────┐
│ Git commit                   │
│ "cleaned_parquet version A"  │
└──────────────────────────────┘
```

# 4. Update Existing Data Content
When you write
```python
df.write.mode("overwrite").parquet("data/cleaned_parquet")
```

New Data
```text
Snapshot 2 candidate: cleaned_parquet version B

data/cleaned_parquet/
├── part-00000-new.parquet
├── part-00001-new.parquet
├── part-00002-new.parquet
└── _SUCCESS
```

Then you run
```bash
dvc status
```

No new snapshot has been saved yet
```bash
data/cleaned_parquet changed
```

Then you run
```bash
dvc add data/cleaned_parquet
```

Now DVC update the pointer
```text
Before:

data/cleaned_parquet.dvc
└── points to directory hash: HASH_A

After:

data/cleaned_parquet.dvc
└── points to directory hash: HASH_B
```

Then you run
```bash
git add data/cleaned_parquet.dvc
git commit -m "Update cleaned parquet snapshot"
```

A new Snapshot is saved

# 5. Summarize for (2)(3)(4)
```text
Time 1
──────────────────────────────────────────────────────────────

Real data:
  cleaned_parquet = version A

Command:
  dvc add data/cleaned_parquet
  git commit -m "Track cleaned parquet v1"

Git stores:
  data/cleaned_parquet.dvc → HASH_A

DVC cache stores:
  HASH_A data objects


Time 2
──────────────────────────────────────────────────────────────

You run Spark cleaning again.

Real data:
  cleaned_parquet = version B

Command:
  dvc status

Result:
  DVC says cleaned_parquet changed

No snapshot yet.


Time 3
──────────────────────────────────────────────────────────────

Command:
  dvc add data/cleaned_parquet
  git add data/cleaned_parquet.dvc
  git commit -m "Update cleaned parquet v2"

Git stores:
  data/cleaned_parquet.dvc → HASH_B

DVC cache stores:
  HASH_A and HASH_B objects if both versions still exist
```

# 6. Types of Command Used in the Pipeline
```text
dvc init
  Creates DVC project structure.
  Not a data snapshot.

dvc cache dir ...
  Changes where DVC cache lives.
  Not a data snapshot.

dvc add data/cleaned_parquet
  Creates or updates DVC metadata for a data snapshot.

git commit data/cleaned_parquet.dvc
  Saves that snapshot in Git history.

dvc status
  Checks whether data changed.
  Does not create a snapshot.

dvc push
  Copies cached data to a DVC remote.
  Does not create a new snapshot.

dvc pull
  Downloads cached data from remote.
  Does not create a new snapshot.

dvc checkout
  Restores workspace data to match current Git/DVC metadata.
  Does not create a new snapshot.

dvc repro
  Later: runs pipeline stages and updates outputs.
  Can create/update snapshot metadata through dvc.lock.
```

# 7.Current Workflow
```text
NO dvc.yaml file

Run notebook/script
        │
        ▼
Parquet folder changes on Lustre
        │
        ▼
dvc status
        │
        ▼
dvc add data/some_folder
        │
        ▼
git add data/some_folder.dvc
        │
        ▼
git commit -m "Update some_folder snapshot"
        │
        ▼
optional: dvc push
```

Example:
```text
cd /home/bguo3/bguo3/DSC-288R-Capstone-Final-Project

dvc status

dvc add data/feature_engineered_parquet

git add data/feature_engineered_parquet.dvc data/.gitignore

git commit -m "Track feature engineered parquet snapshot"
```