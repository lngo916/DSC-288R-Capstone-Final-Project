# -----------------------------
# Import Modules
# -----------------------------
from __future__ import annotations

from typing import Iterable

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.ml.feature import VectorAssembler

# --------------------------------
# Feature Engineered Column Names
# -------------------------------
LABEL_COL = "churn"
FEATURE_COL = "finalized_features"
SCALED_FEATURE_COL = "scaled_features"
WEIGHT_COL = "class_weight"

# -----------------------------
# Feature Engineering Constants
# -----------------------------
SECONDS_PER_DAY = 86_400

# Reusable Columns
FEATURE_ENGINEERING_INPUT_COLS = [
    # Entity keys
    "author_steamid",
    "appid",

    # User profile / activity counts
    "author_num_games_owned",
    "author_num_reviews",

    # Playtime engagement
    "author_playtime_forever",
    "author_playtime_at_review",
    "author_playtime_last_two_weeks",

    # Temporal / recency inputs
    "author_last_played",
    "timestamp_created",
    "timestamp_updated",

    # Review behavior / sentiment proxy
    "review",
    "voted_up",
    "language",

    # Review engagement
    "votes_up",
    "votes_funny",
    "weighted_vote_score",
    "comment_count",

    # Optional metadata
    "written_during_early_access",
]
NUMERIC_COLS = [
    "author_num_games_owned",
    "author_num_reviews",
    "author_playtime_forever",
    "author_playtime_last_two_weeks",
    "author_playtime_at_review",
    "votes_up",
    "votes_funny",
    "comment_count",
    "weighted_vote_score",
]


# ---------------------------------------------------------------------
# Proxy churn label
# ---------------------------------------------------------------------
def create_label(
    df: DataFrame,
    recent_playtime_col: str = "author_playtime_last_two_weeks",
    threshold_minutes: int = 60,
    label_col: str = LABEL_COL,
) -> DataFrame:
    """
    Add a simple proxy churn label.

    churn = 1 means inactive / churned
    churn = 0 means active / retained
    """

    return (
        df.withColumn(
            label_col,
            F.when(F.col(recent_playtime_col).isNull(), F.lit(1.0))
            .when(F.col(recent_playtime_col) >= F.lit(threshold_minutes), F.lit(0.0))
            .otherwise(F.lit(1.0))
        )
        .drop(recent_playtime_col)
    )


# ---------------------------------------------------------------------
# Class weights
# ---------------------------------------------------------------------
def create_class_weights(
    df: DataFrame, 
    label_col=LABEL_COL, 
    weight_col=WEIGHT_COL
) -> DataFrame:
    
    counts = {
        row[label_col]: row["count"]
        for row in df.groupBy(label_col).count().collect()
    }

    total = float(sum(counts.values()))
    n_classes = float(len(counts))

    weights = {
        label: total / (n_classes * count)
        for label, count in counts.items()
    }

    mapping_expr = F.create_map(
        *[
            x
            for label, weight in weights.items()
            for x in (F.lit(float(label)), F.lit(float(weight)))
        ]
    )

    return df.withColumn(
        weight_col,
        mapping_expr[F.col(label_col).cast("double")]
    )


# ---------------------------------------------------------------------
# Review features
# ---------------------------------------------------------------------
def create_review_behavior_features(
    df: DataFrame
) -> DataFrame:
    """
    Add review-text and review-sentiment proxy features.

    These are not NLP sentiment scores. They are lightweight behavioral
    indicators from available Steam review metadata.
    """
    out = df

    if "review" in out.columns:
        # Compute the character length of review
        out = out.withColumn(
            "review_length",
            F.when(F.col("review").isNull(), 0)
            .otherwise(F.length(F.col("review")))
        )

    if "voted_up" in out.columns:
        # Sentiment proxy, not actual sentiment score from Vader
        out = out.withColumn(
            "review_positive",
            F.when(F.col("voted_up").isNull(), None)
             .otherwise(F.col("voted_up").cast("int"))
        )

    return out


# ---------------------------------------------------------------------
# Engagement features
# ---------------------------------------------------------------------
def create_engagement_features(
    df: DataFrame
) -> DataFrame:
    """
    Add playtime-based engagement features.
    """
    out = df

    required = {
        "author_playtime_forever",
        "author_playtime_at_review",
    }

    if required.issubset(set(out.columns)):
        print("I am in")
        forever = F.col("author_playtime_forever").cast("double")
        last_2w = F.col("author_playtime_last_two_weeks").cast("double")
        at_review = F.col("author_playtime_at_review").cast("double")

        # playtime_recent_share = last_two_weeks / forever
        out = out.withColumn(
            "playtime_recent_share",
            F.when((forever.isNull()) | (forever <= 0), 0)
            .otherwise(last_2w / forever)
        )

        # playtime_at_review_share = max(at_review / forever)
        out = out.withColumn(
            "playtime_at_review_share",
            F.when((forever.isNull()) | (forever <= 0), 0)
            .otherwise(at_review / forever)
        )

        # playtime_after_review = forever - at_review
        out = out.withColumn(
            "playtime_after_review",
            F.when(forever.isNull() | at_review.isNull(), 0)
            .otherwise(F.greatest(forever - at_review, F.lit(0.0)))
        )

        # (forever - at_review) / at_review
        out = out.withColumn(
            "playtime_growth_ratio_after_review",
            F.when((at_review.isNull()) | (at_review <= 0), 0)
            .otherwise((forever - at_review) / at_review)
        )

    return out


# ---------------------------------------------------------------------
# Logarithmic transformation features
# ---------------------------------------------------------------------
def transform_log_features(
    df: DataFrame,
    cols: Iterable[str] = NUMERIC_COLS,
    drop_original: bool = False,
) -> DataFrame:
    """
    Add log1p versions of skewed numeric columns.

    log1p(x) = log(1 + x), safer for zero-heavy count/playtime columns.

    Parameters
    ----------
    df:
        Input Spark DataFrame.
    cols:
        Columns to log-transform. If None, uses default skewed numeric columns.
    drop_original:
        If True, remove the original source columns after creating log columns.
        If False, keep both original and log-transformed columns.
    """
    out = df

    # Define columns list
    selected_cols = list(cols)
    if not selected_cols:
        raise ValueError(
            "No available feature columns found for Log Transform Feature Creator."
        )
    transformed_cols = []

    for src in selected_cols:
        if src not in out.columns:
            continue

        log_col = f"log_{src}"
        transformed_cols.append(src)

        out = out.withColumn(
            log_col,
            F.when(F.col(src).isNull(), 0.0)
             .when(F.col(src) < 0, 0.0)
             .otherwise(F.log1p(F.col(src).cast("double")))
        )

    if drop_original and transformed_cols:
        out = out.drop(*transformed_cols)

    return out


# ---------------------------------------------------------------------
# Assemble features
# ---------------------------------------------------------------------
def assemble_features(
    df: DataFrame,
    feature_cols: Iterable[str] = FEATURE_ENGINEERING_INPUT_COLS,
    output_col: str = "finalized_features",
    handle_invalid: str = "keep",
    strict: bool = False,
) -> DataFrame:
    """
    Assemble numeric feature columns into a Spark ML feature vector.

    Parameters
    ----------
    df:
        Input Spark DataFrame after feature engineering.
    feature_cols:
        List of feature columns to assemble. If None, uses
        DEFAULT_MODEL_FEATURE_COLS.
    output_col:
        Name of the assembled feature vector column.
        Default matches your ML_modeling.py convention: finalized_features.
    handle_invalid:
        VectorAssembler invalid handling.
        Options: "error", "skip", "keep".
    strict:
        If True, raise an error if any requested feature columns are missing.
        If False, use only columns that exist in df.

    Returns
    -------
    DataFrame
        DataFrame with a new vector column.
    """
    print(feature_cols)

    # Handle missing features
    existing_cols = set(df.columns)
    print(existing_cols)

    missing_cols = [c for c in feature_cols if c not in existing_cols]
    if strict and missing_cols:
        raise ValueError(
            "Missing expected model feature columns: "
            f"{missing_cols}"
        )
    print(missing_cols)

    # Use Available features
    available_cols = [c for c in feature_cols if c in existing_cols]
    print(available_cols)
    if not available_cols:
        raise ValueError(
            "No available feature columns found for Feature Assembler."
        )

    out = df

    # Cast booleans/numerics safely to double.
    for c in available_cols:
        out = out.withColumn(c, F.col(c).cast("double"))

    assembler = VectorAssembler(
        inputCols=available_cols,
        outputCol=output_col,
        handleInvalid=handle_invalid,
    )

    out = assembler.transform(out)

    return out


# ---------------------------------------------------------------------
# Column Selection
# ---------------------------------------------------------------------
def reduce_features(
    df: DataFrame,
    cols: Iterable[str] | None = None,
    strict: bool = False,
) -> DataFrame:
    """
    Select only the columns needed before feature engineering.

    This helps:
    - reduce memory pressure
    - avoid carrying unused columns through the pipeline
    - make feature engineering input explicit and reproducible

    Parameters
    ----------
    df:
        Input Spark DataFrame.
    cols:
        Optional custom list of columns. If None, uses
        FEATURE_ENGINEERING_INPUT_COLS.
    strict:
        If True, raise an error when expected columns are missing.
        If False, silently select only columns that exist.

    Returns
    -------
    DataFrame
        Spark DataFrame with selected columns only.
    """

    # Define selected columns
    selected_cols = list(cols) if cols is not None else FEATURE_ENGINEERING_INPUT_COLS

    # Handle missing columns
    existing_cols = set(df.columns)
    missing_cols = [c for c in selected_cols if c not in existing_cols]
    if strict and missing_cols:
        raise ValueError(
            "Missing expected feature-engineering input columns: "
            f"{missing_cols}"
        )

    # Use available columns
    available_cols = [c for c in selected_cols if c in existing_cols]
    if not available_cols:
        raise ValueError(
            "No available feature columns found for Feature Reducer."
        )

    # Reduce feature space 
    # Use list unpacking because in case the iterable contains mix type
    return df.select(*available_cols)


# ---------------------------------------------------------------------
# 5. Build model-ready matrix
# ---------------------------------------------------------------------
# def build_proxy_churn_model_frame(
#     df: DataFrame,
#     use_class_weight: bool = True,
# ) -> DataFrame:
#     """
#     Build a model-ready DataFrame for a quick non-temporal baseline.

#     This is NOT the final time-aware churn definition.
#     It is a cleaned-up version of your current quick baseline.

#     Returns columns:
#     - finalized_features
#     - churn
#     - class_weight, optional
#     """

#     # Since author_playtime_last_two_weeks creates the label,
#     # it is intentionally excluded from the feature list.
#     raw_numeric_features = [
#         "author_num_games_owned",
#         "author_num_reviews",
#         "author_playtime_forever",
#         "author_playtime_at_review",
#         "author_last_played",
#         "votes_up",
#         "votes_funny",
#         "weighted_vote_score",
#         "comment_count",
#         "timestamp_created",
#         "timestamp_updated",
#     ]

#     skewed_cols = [
#         "author_num_games_owned",
#         "author_num_reviews",
#         "author_playtime_forever",
#         "author_playtime_at_review",
#         "votes_up",
#         "votes_funny",
#         "comment_count",
#     ]

#     out = df

#     out = add_proxy_churn_label_from_recent_playtime(out)
#     out = log_scale(out, skewed_cols)

#     feature_cols = [
#         # log versions for skewed count/playtime fields
#         "log_author_num_games_owned",
#         "log_author_num_reviews",
#         "log_author_playtime_forever",
#         "log_author_playtime_at_review",
#         "log_votes_up",
#         "log_votes_funny",
#         "log_comment_count",

#         # keep bounded / timestamp / boolean numeric fields
#         "author_last_played",
#         "weighted_vote_score",
#         "timestamp_created",
#         "timestamp_updated",
#         "voted_up_num",
#         "written_during_early_access_num",
#     ]

#     # Keep only columns that actually exist.
#     feature_cols = [c for c in feature_cols if c in out.columns]

#     # Simple null handling for baseline.
#     # Later, replace this with Imputer for numeric features.
#     out = out.fillna(0, subset=feature_cols)

#     assembler = VectorAssembler(
#         inputCols=feature_cols,
#         outputCol=FEATURE_COL,
#         handleInvalid="keep",
#     )

#     out = assembler.transform(out)

#     selected_cols = [FEATURE_COL, LABEL_COL]

#     # if use_class_weight:
#     #     out = add_balanced_class_weights(out)
#     #     selected_cols.append(WEIGHT_COL)

#     return out.select(*selected_cols)


# ----------------------------------------------------------------------------
# Timestamp features (WILL BE MOVED TO DATA PREPARATION IN FUTURE DEVELOPMENT)
# ----------------------------------------------------------------------------
def add_timestamp_columns(
    df: DataFrame
) -> DataFrame:
    """
    Convert Unix epoch-second timestamp columns into Spark timestamp columns.

    Input columns expected:
    - author_last_played
    - timestamp_created
    - timestamp_updated
    """
    out = df

    # Define the timestamp and their name
    timestamp_cols = [
        ("author_last_played", "author_last_played_ts"),
        ("timestamp_created", "timestamp_created_ts"),
        ("timestamp_updated", "timestamp_updated_ts"),
    ]

    # Convert to time stamp type
    for src, dst in timestamp_cols:
        if src in out.columns:
            out = out.withColumn(
                dst, F.to_timestamp(F.from_unixtime(F.col(src)))
            )

    return out


# --------------------------------------------------------------------------------------------------------------------------------------
# Temporal recency features (WILL BE USED WITH TIME-AWARED TRAIN/TEST SPLIT, TIME-AWARED CHURN DEFITION, IN FUTURE PREPARATION)
# --------------------------------------------------------------------------------------------------------------------------------------
def add_recency_features(
    df: DataFrame, 
    cutoff_ts: int | float
) -> DataFrame:
    """
    Add leakage-aware recency features relative to feature cutoff T.

    Parameters
    ----------
    df:
        Spark DataFrame containing Unix epoch-second columns.
    cutoff_ts:
        Feature cutoff time T, represented as Unix epoch seconds.
    """
    out = df

    cutoff = F.lit(float(cutoff_ts))

    if "author_last_played" in out.columns:
        out = out.withColumn(
            "days_since_last_play",
            F.when(F.col("author_last_played").isNull(), None)
             .otherwise((cutoff - F.col("author_last_played").cast("double")) / SECONDS_PER_DAY)
        )

    if "timestamp_created" in out.columns:
        out = out.withColumn(
            "days_since_review_created",
            F.when(F.col("timestamp_created").isNull(), None)
             .otherwise((cutoff - F.col("timestamp_created").cast("double")) / SECONDS_PER_DAY)
        )

    if {"author_last_played", "timestamp_created"}.issubset(set(out.columns)):
        out = out.withColumn(
            "days_between_review_and_last_play",
            F.when(
                F.col("author_last_played").isNull() | F.col("timestamp_created").isNull(),
                None
            ).otherwise(
                (F.col("author_last_played").cast("double") - F.col("timestamp_created").cast("double"))
                / SECONDS_PER_DAY
            )
        )

    return out


# FUTURE DEVELOPMENT
def add_flagged_features():
    pass
