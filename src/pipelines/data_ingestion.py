# -----------------------------
# Import Modules
# -----------------------------
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DataType

from pathlib import Path

import kagglehub
from src.utils.io_utils import read_spark_csv
from src.utils.pyspark_utils import BASE_SCHEMA

# -----------------------------
# Ingestion Constant
# -----------------------------
CSV_OPTIONS = {
    "header": "true",
    "inferSchema": "false",
    "multiLine": "true",
    "escape": '"',
    "quote": '"',
}

# -----------------------------
# Ingestion Logic
# -----------------------------
def ingest_steam_reviews_kaggle(
    path: Path | str,
    dataset: str,
    use_cached: bool = True,
) -> Path:
    """
    Download the Steam reviews Kaggle dataset into the project raw CSV root.

    Parameters
    ----------
    paths:
        Paths/string object for the current environment.
    dataset:
        Kaggle dataset slug.
    use_cached:
        If True, reuse existing cached download when possible.

    Returns
    -------
    Path
        Local path where Kaggle placed the dataset files.
    """
    downloaded_path = kagglehub.dataset_download(
        dataset,
        output_dir=str(path),
        force_download=not use_cached,
    )

    return Path(downloaded_path)

def ingest_steam_reviews_csv(
    spark,
    csv_path: str | Path,
    schema: dict[str, DataType] = BASE_SCHEMA
) -> DataFrame:
    """
    Read raw Steam reviews CSV data and cast known columns to the project schema.

    Notes
    -----
    read_spark_csv intentionally only performs generic CSV loading.
    This function adds project-specific schema enforcement.
    """

    # Read CSV file
    raw_df = read_spark_csv(
        spark=spark,
        path=csv_path,
        options=CSV_OPTIONS,
    )

    # Define schema
    existing_cols = set(raw_df.columns)
    cast_exprs = [
        F.col(c).cast(dtype).alias(c)
        for c, dtype in schema.items()
        if c in existing_cols
    ]

    # Apply schema
    return raw_df.select(*cast_exprs)