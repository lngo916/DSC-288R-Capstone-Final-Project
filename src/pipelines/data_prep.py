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
TEMPORAL_COLS = [
    "author_last_played",
    "timestamp_created",
    "timestamp_updated",
]

VOTES_FUNNY_ARTIFACT_THRESHOLD = 4_000_000_000  # Close to unsigned integer overflow
MAX_2W_MINUTES = 14 * 24 * 60  # Time for 2 week
MIN_REASONABLE_UNIX_TS = 1_000_000_000  # Represent 2001-09-09, this indicate a rough beginning of steam activity in history
VALID_SCORE_RANGE = (0, 1)  # Valid score range define as format: (min score, max score)

# -----------------------------
# Health preparation logic
# -----------------------------
# Type conversion
def enforce_schema(
    df: DataFrame, 
    schema: dict[str, DataType] = BASE_SCHEMA, 
    keep_extra_cols: bool = False
) -> DataFrame:
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
def remove_missing(
    df: DataFrame
) -> DataFrame:
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

def remove_missing_core_keys(
    df: DataFrame, 
    required_cols: Iterable[str] = REQUIRED_CORE_COLS
) -> DataFrame:
    
    # Initialize the binary mask as all ones vector
    condition = F.lit(True)

    # If one row has at least one selected column with missing value, you return that row as 0
    for c in required_cols:
        if c in df.columns:
            condition = condition & F.col(c).isNotNull()

    # Remove through filtering
    return df.filter(condition)

# Duplicate rows/reviews removal
def remove_duplicate_rows(
    df: DataFrame
) -> DataFrame:       
    return df.dropDuplicates()

def remove_duplicate_reviews(
    df: DataFrame, 
    dup_key_cols: Iterable[str] = DUP_KEY_COLS, 
    updated_col: str = "timestamp_updated"
) -> DataFrame:
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

# Consistency cleaning
def remove_playtime_consistency(
    df: DataFrame, 
    playtime_cols: Iterable[str] = PLAYTIME_COLS
) -> DataFrame:
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
    return df.filter(~(at_review_bad | two_week_bad))

def remove_timestamp_consistency(
    df: DataFrame
) -> DataFrame:
    required = {"timestamp_created", "timestamp_updated"}

    # Ensure columns exist in the input df
    if not required.issubset(set(df.columns)):
        return df

    # Find invalid instances where time stamp created > time stamp updated
    invalid = (
        F.col("timestamp_created").isNotNull()
        & F.col("timestamp_updated").isNotNull()
        & (F.col("timestamp_created") > F.col("timestamp_updated"))
    )

    return df.filter(~invalid)  

def remove_playtime_forever_decreases_over_time(
    df: DataFrame
) -> DataFrame:
    required = {
        "author_steamid",
        "appid",
        "timestamp_created",
        "author_playtime_forever",
    }

    # Ensure columns exist in the input df
    if not required.issubset(set(df.columns)):
        return df

    # Groupby + Transform to create window function
    w = (
        Window
        .partitionBy("author_steamid", "appid")
        .orderBy("timestamp_created")
    )

    # Create fields to compute binary vector based on 
    # whether invalid player time decrease over time
    marked = (
        df.withColumn(
            "_prev_playtime_forever",
            F.lag("author_playtime_forever").over(w)
        )
        .withColumn(
            "_playtime_decreases",
            F.col("_prev_playtime_forever").isNotNull()
            & F.col("author_playtime_forever").isNotNull()
            & (F.col("author_playtime_forever") < F.col("_prev_playtime_forever"))
        )
    )

    # Filter through removing and drop extra cols
    return (
        marked.filter(~F.col("_playtime_decreases"))
              .drop("_prev_playtime_forever", "_playtime_decreases")
    )

def remove_users_with_zero_min_reviews(df: DataFrame) -> DataFrame:
    required = {"author_steamid", "author_num_reviews"}

    # Ensure columns exist in the input df
    if not required.issubset(set(df.columns)):
        return df

    # A bad user mean a user whose minimum observed author_num_reviews is <= 0
    bad_users = (
        df.groupBy("author_steamid")
          .agg(F.min("author_num_reviews").alias("min_author_num_reviews"))
          .filter(
              F.col("author_steamid").isNotNull()
              & F.col("min_author_num_reviews").isNotNull()
              & (F.col("min_author_num_reviews") <= 0)
          )
          .select("author_steamid")
    )

    
    # A broadcast join might be needed
    return df
    # return df.join(bad_users, on="author_steamid", how="left_anti")

# Validity cleaning
def remove_negative_count_values(
    df: DataFrame, 
    count_cols: Iterable[str] = NUMERIC_COUNT_COLS
) -> DataFrame:
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
    return df.filter(condition)
    
def remove_invalid_timestamps(
    df: DataFrame, 
    timestamp_cols: Iterable[str] = TEMPORAL_COLS,
    valid_cutoff: int = MIN_REASONABLE_UNIX_TS
) -> DataFrame:
    # Initialize the binary mask as all ones vector
    condition = F.lit(True)

    # If one row has at least one column with nonpositive value, you return that row as 0
    for c in timestamp_cols:
        if c in df.columns:
            condition = condition & (
                F.col(c).isNull() | (F.col(c) > valid_cutoff)
            )

    # Remove invalid instances through filtering
    return df.filter(condition)

def remove_invalid_weighted_vote_score(
    df: DataFrame, 
    valid_range: tuple[int, int] = VALID_SCORE_RANGE
) -> DataFrame:
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
        ~F.col(c).between(valid_range[0], valid_range[1])
    )

    # Removal through filtering
    return df.filter(~invalid)

# Anomaly cleaning
def remove_impossible_vote_funny(
    df: DataFrame, 
    threshold: int = VOTES_FUNNY_ARTIFACT_THRESHOLD
) -> DataFrame:
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

def remove_impossible_two_week_playtime(
    df: DataFrame
) -> DataFrame:
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
    return df.filter(~is_impossible)

# Text cleaning
def clean_review_text_basic(
    df: DataFrame, 
    col_name: str = "review"
) -> DataFrame:
    if col_name not in df.columns:
        return df

    # Remove escape characters
    cleaned = F.regexp_replace(F.col(col_name), r"[\r\n\t]+", " ")
    # Remove multi-spaces
    cleaned = F.regexp_replace(cleaned, r"\s+", " ")
    # Remove trailing & ending spaces
    cleaned = F.trim(cleaned)

    return df.withColumn(col_name, cleaned)


## FOR FUTURE DEVELOPMENT
# Unify drop/flag action, unify consistency/validity check function
# check required columns
# define invalid predicate
# apply action:
#     drop rows
#     flag rows
#     null values

# data_quality_rules.py
#     one source of truth

# data_preparation.py
#     applies rules with action="drop"

# feature_engineering.py
#     applies rules with action="flag"

# data_health_audit.py
#     reports rules