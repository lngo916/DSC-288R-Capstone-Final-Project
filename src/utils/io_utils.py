# src/utils/io_utils.py

from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
from pyspark.sql import DataFrame as SparkDataFrame


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
    Read a CSV file/folder using Spark.
    """
    options = options or {
        "header": "true",
        "inferSchema": "false",
    }

    df = spark.read.options(**options).csv(path)
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