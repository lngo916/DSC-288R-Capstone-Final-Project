from __future__ import annotations

from typing import Iterable

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.ml.feature import VectorAssembler


LABEL_COL = "churn"
FEATURE_COL = "finalized_features"
SCALED_FEATURE_COL = "scaled_features"
WEIGHT_COL = "class_weight"

SECONDS_PER_DAY = 86_400


# ---------------------------------------------------------------------
# 1. Temporary / proxy churn label
# ---------------------------------------------------------------------
def add_proxy_churn_label_from_recent_playtime(
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

    return df.withColumn(
        label_col,
        F.when(F.col(recent_playtime_col).isNull(), F.lit(1.0))
         .when(F.col(recent_playtime_col) > F.lit(threshold_minutes), F.lit(0.0))
         .otherwise(F.lit(1.0))
    )


# ---------------------------------------------------------------------
# Review features
# ---------------------------------------------------------------------
def add_review_behavior_features(df: DataFrame) -> DataFrame:
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
def add_playtime_engagement_features(df: DataFrame) -> DataFrame:
    """
    Add playtime-based engagement features.
    """
    out = df

    required = {
        "author_playtime_forever",
        "author_playtime_last_two_weeks",
        "author_playtime_at_review",
    }

    if required.issubset(set(out.columns)):
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
# Scale numeric feature through Logarithmic transformation
# ---------------------------------------------------------------------
def log_scale(df: DataFrame, cols: Iterable[str] | None = None) -> DataFrame:
    """
    Add log1p versions of skewed numeric columns.

    log1p(x) = log(1 + x), safer for zero-heavy count/playtime columns.
    """
    out = df

    # Define chosen columns
    default_cols = [
        "votes_up",
        "votes_funny",
        "comment_count",
        "author_num_reviews",
        "author_num_games_owned",
        "author_playtime_forever",
        "author_playtime_last_two_weeks",
        "author_playtime_at_review",
        "review_length",
        "playtime_after_review",
    ]
    selected_cols = list(cols) if cols is not None else default_cols

    # Iterate all columns
    for src in selected_cols:
        if src not in out.columns:
            continue

        # Compute log-transform
        out = out.withColumn(
            f"log_{src}",
            F.when(F.col(src).isNull(), 0)
            .when(F.col(src) < 0, 0)
            .otherwise(F.log1p(F.col(src).cast("double")))
        )

    return out


# ---------------------------------------------------------------------
# 5. Build model-ready matrix
# ---------------------------------------------------------------------
def build_proxy_churn_model_frame(
    df: DataFrame,
    use_class_weight: bool = True,
) -> DataFrame:
    """
    Build a model-ready DataFrame for a quick non-temporal baseline.

    This is NOT the final time-aware churn definition.
    It is a cleaned-up version of your current quick baseline.

    Returns columns:
    - finalized_features
    - churn
    - class_weight, optional
    """

    # Since author_playtime_last_two_weeks creates the label,
    # it is intentionally excluded from the feature list.
    raw_numeric_features = [
        "author_num_games_owned",
        "author_num_reviews",
        "author_playtime_forever",
        "author_playtime_at_review",
        "author_last_played",
        "votes_up",
        "votes_funny",
        "weighted_vote_score",
        "comment_count",
        "timestamp_created",
        "timestamp_updated",
    ]

    skewed_cols = [
        "author_num_games_owned",
        "author_num_reviews",
        "author_playtime_forever",
        "author_playtime_at_review",
        "votes_up",
        "votes_funny",
        "comment_count",
    ]

    out = df

    out = add_proxy_churn_label_from_recent_playtime(out)
    out = log_scale(out, skewed_cols)

    feature_cols = [
        # log versions for skewed count/playtime fields
        "log_author_num_games_owned",
        "log_author_num_reviews",
        "log_author_playtime_forever",
        "log_author_playtime_at_review",
        "log_votes_up",
        "log_votes_funny",
        "log_comment_count",

        # keep bounded / timestamp / boolean numeric fields
        "author_last_played",
        "weighted_vote_score",
        "timestamp_created",
        "timestamp_updated",
        "voted_up_num",
        "written_during_early_access_num",
    ]

    # Keep only columns that actually exist.
    feature_cols = [c for c in feature_cols if c in out.columns]

    # Simple null handling for baseline.
    # Later, replace this with Imputer for numeric features.
    out = out.fillna(0, subset=feature_cols)

    assembler = VectorAssembler(
        inputCols=feature_cols,
        outputCol=FEATURE_COL,
        handleInvalid="keep",
    )

    out = assembler.transform(out)

    selected_cols = [FEATURE_COL, LABEL_COL]

    # if use_class_weight:
    #     out = add_balanced_class_weights(out)
    #     selected_cols.append(WEIGHT_COL)

    return out.select(*selected_cols)


# ----------------------------------------------------------------------------
# Timestamp features (WILL BE MOVED TO DATA PREPARATION IN FUTURE DEVELOPMENT)
# ----------------------------------------------------------------------------
def add_timestamp_columns(df: DataFrame) -> DataFrame:
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
def add_recency_features(df: DataFrame, cutoff_ts: int | float) -> DataFrame:
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

