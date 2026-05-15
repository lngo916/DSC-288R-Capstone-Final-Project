# -----------------------------
# Import Modules
# -----------------------------
from pyspark.sql import functions as F

# -----------------------------
# Train/Test Split constants
# -----------------------------
SECONDS_PER_DAY = 86400

# ----------------------------------
# Train/Validation/Test Split Logic
# ----------------------------------
def random_row_split(df, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=42):
    """
    Randomly split rows into train, validation, and test sets.

    This is the simplest split strategy. It randomly assigns individual review rows
    into train/validation/test, regardless of user identity or timestamp.
    """
    # Ratio sanity check
    total = train_ratio + val_ratio + test_ratio
    if abs(total - 1.0) > 1e-6:
        raise ValueError("train_ratio + val_ratio + test_ratio must equal 1.0")

    # Random split on rows
    train_df, val_df, test_df = df.randomSplit(
        [train_ratio, val_ratio, test_ratio],
        seed=seed
    )
    
    return train_df, val_df, test_df

def random_user_split(
    df,
    user_col="author_steamid",
    train_ratio=0.7,
    val_ratio=0.15,
    test_ratio=0.15,
    seed=42
):
    """
    Randomly split users into train, validation, and test sets.

    All rows from the same user are kept in the same split.
    This helps avoid user-level leakage.
    """
    # Ratio sanity check
    total = train_ratio + val_ratio + test_ratio
    if abs(total - 1.0) > 1e-6:
        raise ValueError("train_ratio + val_ratio + test_ratio must equal 1.0")

    # Gather distinct users
    users = (
        df
        .select(user_col)
        .where(F.col(user_col).isNotNull())
        .distinct()
    )

    # Random split on user
    train_users, val_users, test_users = users.randomSplit(
        [train_ratio, val_ratio, test_ratio],
        seed=seed
    )

    # Apply filtered user back to original data to do the split on data
    train_df = df.join(train_users, on=user_col, how="inner")
    val_df = df.join(val_users, on=user_col, how="inner")
    test_df = df.join(test_users, on=user_col, how="inner")

    return train_df, val_df, test_df

def time_aware_row_split(
    df,
    timestamp_col="timestamp_created",
    train_quantile=0.7,
    val_quantile=0.85,
    relative_error=0.001
):
    """
    Split rows by time.

    Rows before the first cutoff go to train.
    Rows between the first and second cutoff go to validation.
    Rows after the second cutoff go to test.

    This is useful when we want to evaluate how well a model trained on the past
    generalizes to future data.
    """
    # Find 2 cutoff points that cutt the range into three pieces
    train_cutoff, val_cutoff = df.approxQuantile(
        timestamp_col,
        [train_quantile, val_quantile],
        relative_error
    )
    train_cutoff = int(train_cutoff)
    val_cutoff = int(val_cutoff)

    # Use filtering to define data
    # train_df  -> || train_cutoff || -> val_df -> || val_cutoff || -> test_df
    train_df = df.where(F.col(timestamp_col) <= F.lit(train_cutoff))
    val_df = df.where(
        (F.col(timestamp_col) > F.lit(train_cutoff)) &
        (F.col(timestamp_col) <= F.lit(val_cutoff))
    )
    test_df = df.where(F.col(timestamp_col) > F.lit(val_cutoff))

    return train_df, val_df, test_df, train_cutoff, val_cutoff

def build_churn_snapshot(
    df,
    cutoff_ts,
    horizon_days=30,
    user_col="author_steamid",
    event_ts_col="timestamp_created",
    last_played_col="author_last_played"
):
    """
    Build a user-level churn snapshot.

    Features are calculated from events before or at cutoff_ts.
    The label checks whether the user appears again during the future horizon.

    churn = 1 means the user did not return within the horizon.
    churn = 0 means the user did return within the horizon.
    """

    horizon_seconds = horizon_days * SECONDS_PER_DAY
    label_end_ts = cutoff_ts + horizon_seconds

    features = (
        df
        .where(F.col(event_ts_col) <= F.lit(cutoff_ts))
        .groupBy(user_col)
        .agg(
            F.count("*").alias("n_reviews_before_T"),
            F.countDistinct("appid").alias("n_games_reviewed_before_T"),

            F.max(event_ts_col).alias("last_review_ts_before_T"),
            F.min(event_ts_col).alias("first_review_ts_before_T"),

            # Leakage-safe version:
            # only use last_played values that happened before or at cutoff time.
            F.max(
                F.when(
                    F.col(last_played_col) <= F.lit(cutoff_ts),
                    F.col(last_played_col)
                )
            ).alias("last_played_ts_before_T"),

            F.max("author_playtime_forever").alias("max_playtime_forever_before_T"),
            F.avg("author_playtime_at_review").alias("avg_playtime_at_review_before_T"),
            F.max("author_playtime_at_review").alias("max_playtime_at_review_before_T"),

            F.avg(F.col("voted_up").cast("double")).alias("positive_review_rate_before_T"),
            F.avg("weighted_vote_score").alias("avg_weighted_vote_score_before_T"),
            F.sum("votes_up").alias("total_votes_up_before_T"),
            F.sum("comment_count").alias("total_comments_before_T")
        )
        .withColumn(
            "days_since_last_review",
            (F.lit(cutoff_ts) - F.col("last_review_ts_before_T")) / F.lit(SECONDS_PER_DAY)
        )
        .withColumn(
            "days_since_last_played",
            (F.lit(cutoff_ts) - F.col("last_played_ts_before_T")) / F.lit(SECONDS_PER_DAY)
        )
        .withColumn(
            "account_observed_days",
            (F.col("last_review_ts_before_T") - F.col("first_review_ts_before_T")) / F.lit(SECONDS_PER_DAY)
        )
    )

    future_active_users = (
        df
        .where(F.col(event_ts_col) > F.lit(cutoff_ts))
        .where(F.col(event_ts_col) <= F.lit(label_end_ts))
        .select(user_col)
        .distinct()
        .withColumn("active_in_horizon", F.lit(1))
    )

    labeled = (
        features
        .join(future_active_users, on=user_col, how="left")
        .withColumn(
            "active_in_horizon",
            F.coalesce(F.col("active_in_horizon"), F.lit(0))
        )
        .withColumn(
            "churn",
            F.when(F.col("active_in_horizon") == 1, F.lit(0)).otherwise(F.lit(1))
        )
        .drop("active_in_horizon")
    )

    return labeled

def time_aware_churn_snapshot_split(
    df,
    timestamp_col="timestamp_created",
    horizon_days=30,
    train_cutoff_quantile=0.70,
    val_cutoff_quantile=0.80,
    test_cutoff_quantile=0.90,
    relative_error=0.001,
    user_col="author_steamid"
):
    """
    Build train, validation, and test churn snapshots using time-based cutoffs.

    Each split is a user-level supervised learning table:
    - features are built from behavior before cutoff T
    - label is built from activity after T within the horizon
    """

    cutoffs = df.approxQuantile(
        timestamp_col,
        [train_cutoff_quantile, val_cutoff_quantile, test_cutoff_quantile],
        relative_error
    )

    train_cutoff, val_cutoff, test_cutoff = [int(x) for x in cutoffs]

    train_df = build_churn_snapshot(
        df,
        cutoff_ts=train_cutoff,
        horizon_days=horizon_days,
        user_col=user_col,
        event_ts_col=timestamp_col
    )

    val_df = build_churn_snapshot(
        df,
        cutoff_ts=val_cutoff,
        horizon_days=horizon_days,
        user_col=user_col,
        event_ts_col=timestamp_col
    )

    test_df = build_churn_snapshot(
        df,
        cutoff_ts=test_cutoff,
        horizon_days=horizon_days,
        user_col=user_col,
        event_ts_col=timestamp_col
    )

    return train_df, val_df, test_df, train_cutoff, val_cutoff, test_cutoff

# ----------------------------------
# Other Helper
# ----------------------------------
def print_split_summary(name, train_df, val_df, test_df, user_col="author_steamid"):
    """
    Print row and user counts for a split.
    """

    print(f"\n===== {name} =====")

    print("Train rows:", train_df.count())
    print("Validation rows:", val_df.count())
    print("Test rows:", test_df.count())

    if user_col in train_df.columns:
        print("Train users:", train_df.select(user_col).distinct().count())
        print("Validation users:", val_df.select(user_col).distinct().count())
        print("Test users:", test_df.select(user_col).distinct().count())