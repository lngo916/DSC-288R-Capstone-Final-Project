# Define the environment and file to work with
MODE = 'COLABS' # Either 'COLABS', 'LOCAL', 'EXPANSE'
DATA = 'SAMPLE' # Either 'SAMPLE', 'FULL'
FEAT = False # Either True, False binary values
MOUNT_PATH = ''
INPUT_PATH = ''
FILE_NAME = ''

if MODE == 'COLABS' and DATA == 'SAMPLE':
    from google.colab import drive
    drive.mount('/content/drive')
    MOUNT_PATH = '/content/drive/MyDrive'
    INPUT_PATH = '/DSC 288R/Project/data'
elif MODE == 'LOCAL' and DATA == 'SAMPLE':
    INPUT_PATH = '/Users/steveg/Downloads'
elif MODE == 'EXPANSE':
    EXPANSE_ROOT = "/expanse/lustre/scratch/bguo3/temp_project"
    INPUT_PATH = f"file:{EXPANSE_ROOT}/steam_reviews"
elif MODE not in ('COLABS', 'LOCAL', 'EXPANSE'):
    raise Exception("Invalid mode, choose from either ('COLABS', 'LOCAL', 'EXPANSE')")
else:
    raise Exception("Invalid combination of mode/data, when you use 'COLABS'/'LOCAL', you can only choose 'SAMPLE' data")

if DATA == 'SAMPLE':
    if FEAT:
        FILE_NAME = 'feat_sample.parquet'
    else:
        FILE_NAME = 'cleaned_sample.parquet'
elif DATA == 'FULL':
    if FEAT:
        FILE_NAME = 'feat_full.parquet'
    else:
        FILE_NAME = 'cleaned_full.parquet'
else:
    raise Exception("Invalid data options, choose from either ('SAMPLE', 'FULL')")


# Define the path to your Parquet folder, which is 'subsampled_parquet' inside your project folder
parquet_folder_path = f'{MOUNT_PATH}{INPUT_PATH}/{FILE_NAME}'

from pyspark.sql import functions as F

USER_COL = "author_steamid"
EVENT_TS_COL = "timestamp_created"
LAST_PLAYED_COL = "author_last_played"

SECONDS_PER_DAY = 86400


def build_churn_snapshot(
    df,
    cutoff_ts: int,
    horizon_days: int = 30,
    user_col: str = USER_COL,
    event_ts_col: str = EVENT_TS_COL,
):
    """
    Build one supervised churn snapshot.

    Features use rows with event_ts <= cutoff_ts.
    Label checks whether the user appears again in (cutoff_ts, cutoff_ts + horizon).
    """

    horizon_seconds = horizon_days * SECONDS_PER_DAY
    label_end_ts = cutoff_ts + horizon_seconds

    # Convert event_ts_col and LAST_PLAYED_COL to unix timestamps for consistent comparisons
    # within the function scope.
    df_with_epoch_timestamps = df \
        .withColumn(event_ts_col + "_epoch", F.unix_timestamp(F.col(event_ts_col))) \
        .withColumn(LAST_PLAYED_COL + "_epoch", F.unix_timestamp(F.col(LAST_PLAYED_COL)))

    # Use the new epoch columns for filtering and aggregation
    event_ts_col_epoch = event_ts_col + "_epoch"
    last_played_col_epoch = LAST_PLAYED_COL + "_epoch"

    # -----------------------------
    # Feature window: past only
    # -----------------------------
    df_past = (
        df_with_epoch_timestamps
        .where(F.col(event_ts_col_epoch).isNotNull())
        .where(F.col(event_ts_col_epoch) <= F.lit(cutoff_ts))
        .where(F.col(user_col).isNotNull())
    )

    # User-level features
    features = (
        df_past
        .groupBy(user_col)
        .agg(
            F.count("*").alias("n_reviews_before_T"),
            F.countDistinct("appid").alias("n_games_reviewed_before_T"),

            F.max(event_ts_col_epoch).alias("last_review_ts_before_T"),
            F.min(event_ts_col_epoch).alias("first_review_ts_before_T"),

            F.max(last_played_col_epoch).alias("last_played_ts_before_T"),

            F.max("author_playtime_forever").alias("max_playtime_forever_before_T"),
            F.avg("author_playtime_at_review").alias("avg_playtime_at_review_before_T"),
            F.max("author_playtime_at_review").alias("max_playtime_at_review_before_T"),

            F.avg(F.col("voted_up").cast("double")).alias("positive_review_rate_before_T"),
            F.avg("weighted_vote_score").alias("avg_weighted_vote_score_before_T"),
            F.sum("votes_up").alias("total_votes_up_before_T"),
            F.sum("comment_count").alias("total_comments_before_T"),
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

    # -----------------------------
    # Future window: label only
    # -----------------------------
    future_active_users = (
        df_with_epoch_timestamps
        .where(F.col(event_ts_col_epoch) > F.lit(cutoff_ts))
        .where(F.col(event_ts_col_epoch) <= F.lit(label_end_ts))
        .where(F.col(user_col).isNotNull())
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

df_with_long_ts = df.withColumn("timestamp_created_long", F.unix_timestamp(F.col("timestamp_created")))

cutoffs = df_with_long_ts.approxQuantile(
    "timestamp_created_long", # Pass the name of the new column as a string
    [0.70, 0.80, 0.90],
    0.001
)

T_train, T_val, T_test = [int(x) for x in cutoffs]

print("T_train:", T_train)
print("T_val:", T_val)
print("T_test:", T_test)

train_df = build_churn_snapshot(df, cutoff_ts=T_train, horizon_days=30)
val_df   = build_churn_snapshot(df, cutoff_ts=T_val,   horizon_days=30)
test_df  = build_churn_snapshot(df, cutoff_ts=T_test,  horizon_days=30)