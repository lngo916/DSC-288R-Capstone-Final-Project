# -----------------------------
# Import Modules
# -----------------------------
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

# -----------------------------
# Sampling Parameters
# -----------------------------
USER_COL = "author_steamid"
EVENT_TS_COL = "timestamp_created"
USER_SAMPLE_FRACTION = 0.02  # Subset 2%
SEED = 42  # Result is reproducible
T_QUANTILE = 0.95  # Use 95th percentile cutoff
RELATIVE_ERROR = 0.001

# -----------------------------
# Sampling Logic
# -----------------------------
def sample_users(
    df: DataFrame,
    user_col: str = USER_COL,
    fraction: float = USER_SAMPLE_FRACTION,
    seed: int = SEED,
) -> DataFrame:
    """
    Sample distinct users from a Spark DataFrame.

    This supports user-level cluster sampling, where users are sampled first
    and then all their rows are kept.
    """

    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in the range (0, 1].")

    return (
        df
        .select(user_col)
        .where(F.col(user_col).isNotNull())
        .distinct()
        .sample(
            withReplacement=False, 
            fraction=fraction, 
            seed=seed
        )
    )

def sample_time_cutoff(
    df: DataFrame,
    event_ts_col: str=EVENT_TS_COL,
    quantile=T_QUANTILE,
    relative_error=RELATIVE_ERROR,
):

    return df.approxQuantile(
        event_ts_col, 
        [quantile], 
        relative_error
    )[0]

def subsample(
    df: DataFrame,
    sampled_users: DataFrame,
    sampled_time_cutoff: float,
    user_col: str = "author_steamid",
) -> DataFrame:
    """
    Keep all rows belonging to sampled users.
    """

    return (
        df
        .join(
            sampled_users, 
            on=user_col, 
            how="inner"
        )
        .filter(
            F.col(EVENT_TS_COL) <= 
            F.lit(sampled_time_cutoff)
        )
    )