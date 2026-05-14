# src/utils/io_utils.py

from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
from pyspark.sql import DataFrame as SparkDataFrame

# ---------------------------------------------------------------------
# Default Parameters
# ---------------------------------------------------------------------
DEFAULT_CSV_OPTIONS = {
    "header": "true",
    "inferSchema": "false",
}


# ---------------------------------------------------------------------
# Spark IO
# ---------------------------------------------------------------------
def read_spark_parquet(spark, path: str) -> SparkDataFrame:
    """
    Read a Spark parquet dataset.
    """
    df = spark.read.parquet(path)
    print(f"Read Spark parquet from: {path}")
    return df

def read_spark_csv(
    spark,
    path: str,
    options: dict | None = None,
) -> SparkDataFrame:
    """
    Read a CSV file or folder using Spark.

    This function only loads the raw CSV.
    Project-specific schema casting should happen after loading.
    """
    csv_options = DEFAULT_CSV_OPTIONS.copy()

    if options:
        csv_options.update(options)

    df = spark.read.options(**csv_options).csv(path)

    print(f"Read Spark CSV from: {path}")
    return df

def write_spark_parquet(
    df: SparkDataFrame,
    path: str,
    mode: str = "overwrite",
    compression: str = "snappy",
) -> None:
    """
    Write a Spark DataFrame to parquet.
    """
    (
        df.write
        .mode(mode)
        .option("compression", compression)
        .parquet(path)
    )
    print(f"Saved Spark parquet to: {path}")

def write_spark_split_parquets(
    train_df: SparkDataFrame,
    val_df: SparkDataFrame,
    test_df: SparkDataFrame,
    train_path: str,
    val_path: str,
    test_path: str,
    mode: str = "overwrite",
    compression: str = "snappy",
) -> None:
    """
    Write train, validation, and test Spark DataFrames to parquet.
    """
    write_spark_parquet(
        train_df,
        train_path,
        mode=mode,
        compression=compression,
    )

    write_spark_parquet(
        val_df,
        val_path,
        mode=mode,
        compression=compression,
    )

    write_spark_parquet(
        test_df,
        test_path,
        mode=mode,
        compression=compression,
    )

# ---------------------------------------------------------------------
# Pandas IO
# ---------------------------------------------------------------------
def read_pandas_parquet(path: str | Path) -> pd.DataFrame:
    """
    Read a Pandas parquet file/folder.
    Do NOT pass file:/ paths here.
    """
    path = Path(path)
    df = pd.read_parquet(path)
    print(f"Read Pandas parquet from: {path}")
    return df

def write_pandas_parquet(
    df: pd.DataFrame,
    path: str | Path,
    index: bool = False,
    engine: str = "pyarrow",
) -> None:
    """
    Write a Pandas DataFrame to parquet.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(
        path,
        index=index,
        engine=engine,
    )

    print(f"Saved Pandas parquet to: {path}")