# -----------------------------
# Import Modules
# -----------------------------
from __future__ import annotations

# PySpark libs
from pyspark.sql import (
    Window,
    functions as F,
    DataFrame
)
from pyspark.sql.types import DataType

# Other libs
from typing import Iterable
from src.utils.pyspark_utils import BASE_SCHEMA

# -----------------------------
# Preparation constants
# -----------------------------
DUP_KEY_COLS = [
    "author_steamid",
    "appid",
    "timestamp_created",
]
NUMERIC_COUNT_COLS = [
    "author_num_games_owned",
    "author_num_reviews",
    "author_playtime_forever",
    "author_playtime_last_two_weeks",
    "author_playtime_at_review",
    "votes_up",
    "votes_funny",
    "comment_count",
]
PLAYTIME_COLS = [
    "author_playtime_at_review",
    "author_playtime_last_two_weeks",
    "author_playtime_forever",
]
REQUIRED_CORE_COLS = [
    "author_steamid",
    "appid",
    "timestamp_created",
]

VOTES_FUNNY_ARTIFACT_THRESHOLD = 4_000_000_000
MAX_2W_MINUTES = 14 * 24 * 60

# -----------------------------
# Health preparation logic
# -----------------------------
# Type conversion
def enforce_schema(df: DataFrame, schema: dict[str, DataType] = BASE_SCHEMA, keep_extra_cols: bool = False) -> DataFrame:
    """
    Cast known columns to the expected Spark types.

    Notes
    -----
    Spark casts invalid values to null. Always run a null audit after this.

    """

    # Only cast existing columns
    existing_cols = set(df.columns)

    # Casting original to new
    cast_exprs = [
        F.col(c).cast(dtype).alias(c)
        for c, dtype in schema.items()
        if c in existing_cols
    ]

    # Keep original from new
    if keep_extra_cols:
        extra_exprs = [
            F.col(c)
            for c in df.columns
            if c not in schema
        ]
        return df.select(*cast_exprs, *extra_exprs)

    return df.select(*cast_exprs)

# Missing value removal
def remove_missing(df: DataFrame) -> DataFrame:
    """
    Remove rows missing the minimum keys needed for review/user/time-level modeling.
    """
    
    # Initialize the binary mask as all ones vector
    condition = F.lit(True)

    # If one row has at least one column with missing value, you return that row as 0
    for c in df.columns:
        condition = condition & F.col(c).isNotNull()

    # Remove through filtering
    return df.filter(condition)

# Invalid outliers removal
def remove_outliers(df: DataFrame, threshold: int = VOTES_FUNNY_ARTIFACT_THRESHOLD,) -> DataFrame:
    """
    Handle votes_funny values likely caused by unsigned 32-bit/API artifacts.

    Recommended default:
      - null the bad value, keep the row.
    This preserves the review while preventing the artifact from poisoning features.
    """

    # Define the column on which you are removing outliers
    c = "votes_funny"
    if c not in df.columns:
        return df

    # Create binary mask for rows with votes_funny outlier values
    is_artifact = (
        (F.col(c).isNotNull()) & 
        (F.col(c) >= F.lit(threshold))
    )

    # Remove through filtering
    return df.filter(~is_artifact)

# Duplicate rows/reviews removal
def remove_duplicate_rows(df: DataFrame) -> DataFrame:       
    return df.dropDuplicates()

def remove_duplicate_reviews(df: DataFrame, dup_key_cols: Iterable[str] = DUP_KEY_COLS, updated_col: str = "timestamp_updated",) -> DataFrame:
    """
    Drop duplicate review events, keeping the row with the most recent timestamp_updated.
    """

    # Ensure columns exist in the input df
    cols = [
        c 
        for c in dup_key_cols 
        if c in df.columns
    ]
    if not cols: 
        return df.dropDuplicates()

    # If update column does not exist, then default to delete any review duplicate
    if updated_col not in df.columns:
        return df.dropDuplicates(cols)

    # Define a window function that rank the same review by most recent update
    w = (
        Window
            .partitionBy(*cols)
            .orderBy(
                F.col(updated_col).desc_nulls_last()
            )
    )

    # For each duplicate group, choose the top 1 version and discard other version
    return (
        df.withColumn("_dup_rank", F.row_number().over(w))
            .filter(F.col("_dup_rank") == 1)
            .drop("_dup_rank")
    )

# Consistency & Validity cleaning
def clean_playtime_consistency(df: DataFrame, playtime_cols: Iterable[str] = PLAYTIME_COLS, strategy: str = "flag",) -> DataFrame:
    """
    Handle rows where:
      - author_playtime_at_review > author_playtime_forever
      - author_playtime_last_two_weeks > author_playtime_forever

    Default is flag instead of drop because these can reflect API timing issues.
    """

    # Ensure columns exist in the input df
    if not set(playtime_cols).issubset(set(df.columns)):
        return df

    # Find inconsistent instances (current playtime < all playtime)
    at_review_bad = (
        F.col("author_playtime_at_review").isNotNull()
        & F.col("author_playtime_forever").isNotNull()
        & (
            F.col("author_playtime_at_review") > 
            F.col("author_playtime_forever")
        )
    )
    two_week_bad = (
        F.col("author_playtime_last_two_weeks").isNotNull()
        & F.col("author_playtime_forever").isNotNull()
        & (
            F.col("author_playtime_last_two_weeks") > 
            F.col("author_playtime_forever")
        )
    )

    # Remove inconsistency instances through filtering
    if strategy == "drop":
        return df.filter(~(at_review_bad | two_week_bad))

    # Keep it as useful columns, used for feature engineering
    if strategy == "flag":
        return (
            df.withColumn(
                "flag_playtime_at_review_gt_forever",
                at_review_bad.cast("boolean")
            )
            .withColumn(
                "flag_playtime_2w_gt_forever",
                two_week_bad.cast("boolean")
            )
        )

    raise ValueError("strategy must be 'flag' or 'drop'")

def clean_negative_count_values(df: DataFrame, count_cols: Iterable[str] = NUMERIC_COUNT_COLS, strategy: str = "flag") -> DataFrame:
    """
    Handle negative values in count-like columns.

    strategy:
      - "null": replace invalid negative values with null
      - "drop": remove rows containing any negative count value
    """

    # Ensure columns exist in the input df
    cols = [
        c 
        for c in count_cols 
        if c in df.columns
    ]

    # Initialize the binary mask as all ones vector
    condition = F.lit(True)

    # If one row has at least one column with negative count, you return that row as 0
    for c in cols:
        condition = condition & (
            F.col(c).isNull() | 
            (F.col(c) >= 0)
        )

    # Remove invalid instances through filtering
    if strategy == "drop":
        return df.filter(condition)
    
    # Keep it as useful columns, used for feature engineering
    if strategy == "flag":
        for c in cols:
            df = df.withColumn(
                f"flag_{c}_negative",
                (
                    F.col(c).isNotNull() &
                    (F.col(c) < 0)
                ).cast("boolean")
            )
        return df

    raise ValueError("strategy must be 'flag' or 'drop'")

def clean_weighted_vote_score(df: DataFrame, strategy: str = "flag") -> DataFrame:
    """
    Ensure weighted_vote_score is in [0, 1].
    """

    # Ensure columns exist in the input df
    c = "weighted_vote_score"
    if c not in df.columns:
        return df

    # Find invalid weighted score outside of range [0.0, 1.0]
    invalid = (
        F.col(c).isNotNull() &
        ~F.col(c).between(0.0, 1.0)
    )

    # Removal through filtering
    if strategy == "drop":
        return df.filter(~invalid)
    
    # Keep it as useful columns, used for feature engineering
    if strategy == "flag":
        return df.withColumn(
            "flag_weighted_vote_score_invalid",
            invalid.cast("boolean")
        )
 
    raise ValueError("strategy must be 'flag' or 'drop'")

def clean_impossible_two_week_playtime(df: DataFrame, strategy: str = "flag") -> DataFrame:
    """
    Handle author_playtime_last_two_weeks > 14 days of minutes.

    Default is flag, because near-limit values may reflect Steam runtime,
    not necessarily active human gameplay.
    """

    # Ensure columns exist in the input df
    c = "author_playtime_last_two_weeks"
    if c not in df.columns:
        return df

    # Find invalid instances where playtime > 2 weeks
    is_impossible = F.col(c).isNotNull() & (F.col(c) > F.lit(MAX_2W_MINUTES))

    # Remove invalid instances through filtering
    if strategy == "drop":
        return df.filter(~is_impossible)
    
    # Keep it as useful columns, used for feature engineering
    if strategy == "flag":
        return df.withColumn(
            "flag_playtime_2w_exceeds_physical_limit",
            is_impossible.cast("boolean")
        )

    raise ValueError("strategy must be 'flag' or 'drop'")