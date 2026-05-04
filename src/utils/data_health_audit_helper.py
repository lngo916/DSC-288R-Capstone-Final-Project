# -----------------------------
# Import Modules
# -----------------------------
from __future__ import annotations

# PySpark libs
from pyspark.sql import (
    Window,
    functions as F,
    DataFrame as SparkDataFrame
)

# Other libs
import pandas as pd
from typing import Iterable, Union, Any, TypeAlias
from src.utils.pyspark_helper import (
    BASE_SCHEMA
)

# -----------------------------
# Define Parameters
# -----------------------------
# Reusable columns
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
CATEGORICAL_COLS = [
    "voted_up",
    "written_during_early_access"
]
DUP_KEY_COLS = [
    "author_steamid", 
    "appid", 
    "timestamp_created"
]

# Reusable type
ReportReturnType: TypeAlias = (
    Union[
        pd.DataFrame,  # Store aggregated info with fixed schema
        list[dict[str, Any]],  # Store aggregated info with flexible schema
        SparkDataFrame,  # Store large-scale info with fixed schema
        dict[str, SparkDataFrame],  # Store list of resulting spark df
        tuple  # Store flexible info
    ]
)
SummaryType: TypeAlias = list[dict[str, Any]]
IssueDfType: TypeAlias = dict[str, SparkDataFrame]

# -----------------------------
# Health audit logic
# -----------------------------
def structure_report(df: SparkDataFrame, row_count: int) -> ReportReturnType:
    """
    TBD
    """
    
    # Count on row, columns, cell
    column_count = len(df.columns)
    cell_count = row_count * column_count
    
    return pd.DataFrame([{
        "row_count": row_count,
        "column_count": column_count,
        "cell_count": cell_count
    }])

def schema_audit(df: SparkDataFrame) -> ReportReturnType:
    """
    TBD
    """
    
    # Set up for reuse
    rows = []
    present_cols = set(df.columns)
    present_coltypes = dict(df.dtypes)

    # For each column, compare if expected and actual type matches
    for c, expected_dtype in BASE_SCHEMA.items():
        actual_dtype = present_coltypes.get(c)
        rows.append({
            "column_name": c,
            "present_in_df": c in present_cols,
            "expected_type": expected_dtype.simpleString(),
            "actual_type": actual_dtype,
            "matches_expected_family": actual_dtype == expected_dtype.simpleString() if actual_dtype is not None else False,
        })

    return pd.DataFrame(rows)

def null_report(df: SparkDataFrame, row_count: int) -> ReportReturnType:
    """
    TBD
    """
    
    # Define expression for readability
    exprs = [
        F.sum(F.col(c).isNull().cast("long")).alias(c) 
        for c in df.columns
    ]
    stack_expr = ", ".join([
        f"'{c}', `{c}`" 
        for c in df.columns
    ])
    
    return (
        # Count missing value counts per column
        df.select(exprs)
            # Organize it to format (column name, count)
            .selectExpr(f"stack({len(df.columns)}, {stack_expr}) as (column_name, null_count)")
            # Compute percentage of missing values
            .withColumn("null_rate", F.col("null_count") / row_count)
            .orderBy(F.desc("null_rate"), F.desc("null_count"))
    )

def consistency_report(df: SparkDataFrame, row_count) -> dict[str, ReportReturnType]:
    """
    Run logical cross-column / over-time consistency checks.

    Returns a dictionary with:
    - report_name: string
    - summary_df: Spark DataFrame with issue counts and rates
    - issue_dfs: dict[str, Spark DataFrame] of violating rows

    TBD
    """

    ## Set up for reuse
    # Count total distinct users once for user-level rates
    total_users = (
        df.select("author_steamid")
          .where(F.col("author_steamid").isNotNull())
          .distinct()
          .count()
    )

    # ============================================================
    # 1. timestamp_created should usually be <= timestamp_updated
    # ============================================================
    # Filter rows where both timestamps exist, and the updated time is earlier than the created time
    issue_ts_order = (
        df.filter(
            F.col("timestamp_created").isNotNull() &
            F.col("timestamp_updated").isNotNull() &
            (F.col("timestamp_created") > F.col("timestamp_updated"))
        )
        .select(
            "author_steamid",
            "appid",
            "timestamp_created",
            "timestamp_updated"
        )
    )
    # Count how many bad rows exist
    count_ts_order = issue_ts_order.count()

    # ============================================================
    # 2A. playtime_at_review should be <= author_playtime_forever
    # ============================================================
    # Check rows where playtime_at_review is greater than lifetime playtime
    issue_playtime_review_gt_forever = (
        df.filter(
            F.col("author_playtime_at_review").isNotNull() &
            F.col("author_playtime_forever").isNotNull() &
            (F.col("author_playtime_at_review") > F.col("author_playtime_forever"))
        )
        .select(
            "author_steamid",
            "appid",
            "author_playtime_at_review",
            "author_playtime_forever",
            "timestamp_created"
        )
    )
    # Count violations
    count_playtime_review_gt_forever = issue_playtime_review_gt_forever.count()

    # ================================================================
    # 2B. playtime_last_two_weeks should be <= author_playtime_forever
    # ================================================================
    # Check rows where last_two_weeks playtime is greater than lifetime playtime
    issue_playtime_2w_gt_forever = (
        df.filter(
            F.col("author_playtime_last_two_weeks").isNotNull() &
            F.col("author_playtime_forever").isNotNull() &
            (F.col("author_playtime_last_two_weeks") > F.col("author_playtime_forever"))
        )
        .select(
            "author_steamid",
            "appid",
            "author_playtime_last_two_weeks",
            "author_playtime_forever",
            "timestamp_created"
        )
    )
    # Count violations
    count_playtime_2w_gt_forever = issue_playtime_2w_gt_forever.count()

    # ============================================================
    # 3) all users should have at least 1 review
    #    We check the minimum author_num_reviews seen per user.
    # ============================================================
    # Group by user and compute the minimum author_num_reviews seen for that user
    # If the minimum is 0, then that user has at least one suspicious row
    issue_user_zero_reviews = (
        df.groupBy("author_steamid")
          .agg(F.min("author_num_reviews").alias("min_author_num_reviews"))
          .filter(
              F.col("author_steamid").isNotNull() &
              F.col("min_author_num_reviews").isNotNull() &
              (F.col("min_author_num_reviews") <= 0)
          )
    )
    # Count suspicious users
    count_user_zero_reviews = issue_user_zero_reviews.count()

    # ==================================================================
    # 4) lifetime playtime should not decrease over time
    #    Compare each row to the previous row within each user-app pair.
    # ==================================================================
    # Define a window:
    # - partition by user and app
    # - order rows by timestamp_created from earliest to latest

    w = Window.partitionBy("author_steamid", "appid").orderBy("timestamp_created")

    # Add previous playtime_forever for comparison against the current row
    df_with_prev = (
        df.select(
            "author_steamid",
            "appid",
            "timestamp_created",
            "author_playtime_forever"
        )
            .filter(
                F.col("author_steamid").isNotNull() &
                F.col("appid").isNotNull() &
                F.col("timestamp_created").isNotNull() &
                F.col("author_playtime_forever").isNotNull()
            )
            .withColumn(
                "prev_playtime_forever",
                F.lag("author_playtime_forever").over(w)
            )
    )

    # Find rows where current lifetime playtime is lower than the previous lifetime playtime
    issue_playtime_decreases = (
        df_with_prev.filter(
            F.col("prev_playtime_forever").isNotNull() &
            (F.col("author_playtime_forever") < F.col("prev_playtime_forever"))
        )
    )
    # Count violations
    count_playtime_decreases = issue_playtime_decreases.count()

    # ============================================================
    # Build the report
    # ============================================================
    # Report statistics
    summary_rows = [
        {
            "issue_name": "timestamp_created_gt_timestamp_updated",
            "violation_count": count_ts_order,
            "violation_rate": _rate(count_ts_order, row_count),
        },
        {
            "issue_name": "author_playtime_at_review_gt_author_playtime_forever",
            "violation_count": count_playtime_review_gt_forever,
            "violation_rate": _rate(count_playtime_review_gt_forever, row_count),
        },
        {
            "issue_name": "author_playtime_last_two_weeks_gt_author_playtime_forever",
            "violation_count": count_playtime_2w_gt_forever,
            "violation_rate": _rate(count_playtime_2w_gt_forever, row_count),
        },
        {
            "issue_name": "users_with_min_author_num_reviews_eq_0",
            "violation_count": count_user_zero_reviews,
            "violation_rate": _rate(count_user_zero_reviews, total_users),
        },
        {
            "issue_name": "author_playtime_forever_decreases_over_time",
            "violation_count": count_playtime_decreases,
            "violation_rate": _rate(count_playtime_decreases, row_count),
        },
    ]
    summary_rows = sorted(
        summary_rows,
        key=lambda row: row["violation_count"],
        reverse=True
    )

    # Report df
    issue_dfs = {
        "timestamp_created_gt_timestamp_updated": issue_ts_order,
        "author_playtime_at_review_gt_author_playtime_forever": issue_playtime_review_gt_forever,
        "author_playtime_last_two_weeks_gt_author_playtime_forever": issue_playtime_2w_gt_forever,
        "users_with_min_author_num_reviews_eq_0": issue_user_zero_reviews,
        "author_playtime_forever_decreases_over_time": issue_playtime_decreases,
    }

    return {
        "summary_rows": summary_rows,
        "issue_dfs": issue_dfs,
    }

def validity_report(df: SparkDataFrame, row_count)-> dict[str, ReportReturnType]:
    """
    Run single-column or bounded-range validity checks.

    Returns a dictionary with:
    - report_name: string
    - summary_df: Spark DataFrame with issue counts and rates
    - issue_dfs: dict[str, Spark DataFrame] of violating rows

    TBD    
    """

    # Set up for reuse
    issue_dfs = {}
    summary_rows = []

    # ============================================================
    # 5) Count-like columns should not be negative
    # Build one issue per column so the report is easier to read.
    # ============================================================
    
    # Iterate all Count-based columns
    for col_name in NUMERIC_COLS[:-1]:
        # Filter column that has negative counts.
        issue_df = (
            df.filter(
                F.col(col_name).isNotNull() &
                (F.col(col_name) < 0)
            )
            .select("author_steamid", "appid", col_name, "timestamp_created")
        )
        # Count violation
        issue_count = issue_df.count()

        # Register report
        issue_name = f"{col_name}_negative"
        summary_rows, issue_dfs = _register_issue(
            issue_name,
            issue_df,
            summary_rows,
            issue_dfs,
            row_count
    )

    # ============================================================
    # 6. weighted_vote_score should be between 0 and 1
    # ============================================================
    # Filter invalid scores:
    # - not null
    # - less than 0 or greater than 1
    issue_weighted_vote_score = (
        df.filter(
            F.col("weighted_vote_score").isNotNull() &
            (
                (F.col("weighted_vote_score") < 0) |
                (F.col("weighted_vote_score") > 1)
            )
        )
        .select(
            "author_steamid",
            "appid",
            "weighted_vote_score",
            "timestamp_created"
        )
    )
    # Count violation
    count_weighted_vote_score = issue_weighted_vote_score.count()

    # Register report
    issue_name = "weighted_vote_score_out_of_range"
    summary_rows, issue_dfs = _register_issue(
            issue_name,
            issue_weighted_vote_score,
            summary_rows,
            issue_dfs,
            row_count
    )

    # ============================================================
    # Build the report
    # ============================================================
    summary_rows = sorted(
        summary_rows,
        key=lambda row: row["violation_count"],
        reverse=True
    )
    return {
        "summary_rows": summary_rows,
        "issue_dfs": issue_dfs,
    }

def anomaly_report(df: SparkDataFrame, row_count) -> dict[str, ReportReturnType]:
    """
    Build an anomaly report for the requested edge cases only.

    Covered issue families
    ----------------------
    1. Numeric summary statistics (for manual outlier inspection)
    2. author_playtime_last_two_weeks >= 90% of 14-day physical max
    3. author_playtime_last_two_weeks > 14-day physical max
    4. votes_funny >= artifact threshold
    5. votes_funny in [artifact threshold, uint32 max)
    6. votes_funny == uint32 max
    7. Largest non-artifact votes_funny value below threshold

    Returns
    -------
    dict with:
      - summary_df
      - issue_dfs
      - numeric_describe_df

    TBD
    """

    # ========================================================
    # Set up for reuse
    # ========================================================
    VOTES_FUNNY_MAX = 2**32 - 1
    VOTES_FUNNY_ARTIFACT_THRESHOLD = 4_000_000_000
    MAX_2W_MINUTES = 14 * 24 * 60
    PLAYTIME_2W_NEAR_LIMIT_THRESHOLD = 0.90 * MAX_2W_MINUTES

    # ========================================================
    # 1. Check for outlier value using summary statistics (Pandas)
    #    This is not an "issue_df", but a global summary table
    #    for manual anomaly / outlier inspection.
    # ========================================================
    numeric_describe_df = df.select(*NUMERIC_COLS).describe()

    # ================================================================================================================
    # 2. Create report regarding anomaly report for suspicious features (1) votes_funny artifact (Pandas)
    # ================================================================================================================
    summary_rows = []
    issue_dfs = {}

    # ========================================================
    # 2A. playtime_last_two_weeks >= 90% of physical maximum
    #     Suspicious, but not automatically wrong
    # ========================================================
    issue_playtime_2w_near_limit = (
        df.filter(
            F.col("author_playtime_last_two_weeks").isNotNull() &
            (F.col("author_playtime_last_two_weeks") >= F.lit(PLAYTIME_2W_NEAR_LIMIT_THRESHOLD))
        )
        .select(
            "author_steamid",
            "appid",
            "author_playtime_last_two_weeks",
            "author_playtime_forever",
            "timestamp_created",
        )
        .orderBy(F.desc("author_playtime_last_two_weeks"))
    )
    summary_rows, issue_dfs = _register_issue(
        "playtime_2w_near_limit",
        issue_playtime_2w_near_limit,
        summary_rows,
        issue_dfs,
        row_count
    )

    # ========================================================
    # 2B. playtime_last_two_weeks > physical maximum
    #     This is stronger than "near limit"
    # ========================================================
    issue_playtime_2w_exceeds_limit = (
        df.filter(
            F.col("author_playtime_last_two_weeks").isNotNull() &
            (F.col("author_playtime_last_two_weeks") > F.lit(MAX_2W_MINUTES))
        )
        .select(
            "author_steamid",
            "appid",
            "author_playtime_last_two_weeks",
            "author_playtime_forever",
            "timestamp_created",
        )
        .orderBy(F.desc("author_playtime_last_two_weeks"))
    )
    summary_rows, issue_dfs = _register_issue(
        "playtime_2w_exceeds_limit",
        issue_playtime_2w_exceeds_limit,
        summary_rows,
        issue_dfs,
        row_count
    )

    # ========================================================
    # 2C. votes_funny >= artifact threshold
    #     Broad suspicious zone
    # ========================================================
    issue_votes_funny_is_uint32_artifact = (
        df.filter(
            F.col("votes_funny").isNotNull() &
            (F.col("votes_funny") >= F.lit(VOTES_FUNNY_ARTIFACT_THRESHOLD))
        )
        .select(
            "author_steamid",
            "appid",
            "votes_funny",
            "votes_up",
            "weighted_vote_score",
            "comment_count",
            "timestamp_created",
        )
        .orderBy(F.desc("votes_funny"))
    )
    summary_rows, issue_dfs = _register_issue(
        "votes_funny_is_uint32_artifact",
        issue_votes_funny_is_uint32_artifact,
        summary_rows,
        issue_dfs,
        row_count
    )

    # ========================================================
    # 2D. votes_funny in [artifact threshold, uint32 max)
    #    Near-exact artifact range, excluding the exact max
    # 3. Check for instances where votes_funny reached max value (Pandas)
    # ========================================================
    issue_votes_funny_near_exact_uint32_artifact_max = (
        df.filter(
            F.col("votes_funny").isNotNull() &
            F.col("votes_funny").between(
                VOTES_FUNNY_ARTIFACT_THRESHOLD,
                VOTES_FUNNY_MAX - 1,   # inclusive upper bound workaround
            )
        )
        .select(
            "author_steamid",
            "appid",
            "votes_funny",
            "votes_up",
            "weighted_vote_score",
            "comment_count",
            "timestamp_created",
        )
        .orderBy(F.desc("votes_funny"))
    )
    summary_rows, issue_dfs = _register_issue(
        "votes_funny_near_exact_uint32_artifact_max",
        issue_votes_funny_near_exact_uint32_artifact_max,
        summary_rows,
        issue_dfs,
        row_count
    )

    # ========================================================
    # 2E. votes_funny == uint32 max
    #     Exact max-value artifact cases
    # 4. Check for instances where votes_funny near max value (Pandas)
    # ========================================================
    issue_votes_funny_exact_uint32_max = (
        df.filter(
            F.col("votes_funny").isNotNull() &
            (F.col("votes_funny") == F.lit(VOTES_FUNNY_MAX))
        )
        .select(
            "author_steamid",
            "appid",
            "votes_funny",
            "votes_up",
            "weighted_vote_score",
            "comment_count",
            "timestamp_created",
        )
        .orderBy(F.desc("votes_funny"))
    )
    summary_rows, issue_dfs = _register_issue(
        "votes_funny_exact_uint32_max",
        issue_votes_funny_exact_uint32_max,
        summary_rows,
        issue_dfs,
        row_count
    )

    # ========================================================
    # 2D. Largest non-artifact votes_funny value below threshold
    #     This reproduces your "proportion compared to max" idea
    # 5. Find the largest vote_funny value that follows right after ARTIFACT_THRESHOLD, compute its propoertion comparing to max value
    # If it's between 60% - 95%, it will indicate broader range of artifact from API and we will need to dive deeper (Pandas)
    # ========================================================
    max_non_artifact_votes_funny = (
        df.filter(
            F.col("votes_funny").isNotNull() &
            (F.col("votes_funny") < F.lit(VOTES_FUNNY_ARTIFACT_THRESHOLD))
        )
        .agg(F.max("votes_funny").alias("max_non_artifact_votes_funny"))
        .collect()[0]
        ["max_non_artifact_votes_funny"]
    )
    max_non_artifact_as_percent_of_uint32_max = (
        max_non_artifact_votes_funny / VOTES_FUNNY_MAX * 100
        if max_non_artifact_votes_funny is not None
        else None
    )

    # ============================================================
    # Build the report
    # ============================================================
    summary_rows = sorted(
        summary_rows,
        key=lambda row: row["violation_count"],
        reverse=True
    )
    return {
        "summary_rows": summary_rows,
        "issue_dfs": issue_dfs,
        "numeric_describe_df": numeric_describe_df,
        "vote_max_non_artifact": (max_non_artifact_votes_funny, max_non_artifact_as_percent_of_uint32_max)
    }

def noise_report(df: SparkDataFrame, row_count: int) -> ReportReturnType:
    """
    Check how often selected numeric columns are zero
    or selected boolean columns are false.
    TBD
    """

    columns = NUMERIC_COLS

    # 
    exprs = [
        F.sum((F.col(c) == 0).cast("long")).alias(c)
        for c in columns
    ]

    stack_expr = ", ".join([
        f"'{c}', `{c}`"
        for c in columns
    ])

    return (
        df.select(exprs)
            # Organize it to format (column name, count)
            .selectExpr(
                f"stack({len(columns)}, {stack_expr}) as (column_name, zero_or_false_count)"
            )
            .withColumn("zero_or_false_rate", F.col("zero_or_false_count") / row_count)
            .orderBy(F.desc("zero_or_false_rate"), F.desc("zero_or_false_count"))
    )

def uniqueness_report(df: SparkDataFrame, row_count: int) -> ReportReturnType:
    """
    TBD
    """
    columns = NUMERIC_COLS + CATEGORICAL_COLS
    
    # Count distance value per column
    exprs = [
            F.countDistinct(c).alias(c)
            for c in columns
        ]
    
    stack_expr = ", ".join([
        f"'{c}', `{c}`" 
        for c in columns
    ])

    return (
        # Aggregate distinct count
        df.agg(*exprs)
            # Organize it to format (column name, count)
            .selectExpr(
                f"stack({len(list(columns))}, {stack_expr}) as (column_name, n_unique)"
            )
            # Unique count & unique rate
            .withColumn("unique_rate", F.col("n_unique") / row_count)
            .orderBy(F.asc("n_unique"), F.asc("unique_rate"))
    )

def duplicate_report(df: SparkDataFrame, row_count) -> dict[str, ReportReturnType]:
    # ============================================================
    # Set up for reuse
    # ============================================================
    distinct_rows = df.distinct().count()
    exact_duplicate_rows = row_count - distinct_rows
    summary_rows = []
    issue_dfs = {}

    # ============================================================
    # Compute duplicate counts per columns
    # ============================================================
    exact_dup_df = (
        df.groupBy(*df.columns)
            .count()
            .filter(F.col("count") > 1)
            .orderBy(F.desc("count"))
    )
    # Register report
    issue_content = {
        "issue_name": "exact_dup",
        "row_count": row_count,
        "distinct_full_rows": distinct_rows,
        "exact_duplicate_rows": exact_duplicate_rows,
        "exact_duplicate_rate": exact_duplicate_rows / row_count if row_count else None,
    }
    summary_rows, issue_dfs = _register_issue(
        "exact_dup", 
        exact_dup_df, 
        summary_rows, 
        issue_dfs, 
        row_count,
        issue_content
    )

    # ============================================================
    # Compute duplicate counts per key columns group
    # ============================================================
    combo_dup_df = (
        df.groupBy(*DUP_KEY_COLS)
            .count()
            .filter(F.col("count") > 1)
            .orderBy(F.desc("count"))
    )
    dup_key_group_count = combo_dup_df.count()
    dup_key_row_count = (
        combo_dup_df.agg(F.sum("count").alias("n")).collect()[0]["n"]
        if dup_key_group_count > 0 else 0
    )
    # Register report
    issue_content = {
        "issue_name": "combo_dup",
        "key_cols": DUP_KEY_COLS,
        "duplicate_key_groups": dup_key_group_count,
        "duplicate_key_rows": dup_key_row_count,
    }
    summary_rows, issue_dfs = _register_issue(
        "combo_dup", 
        combo_dup_df,
        summary_rows, 
        issue_dfs, 
        row_count,
        issue_content
    )

    # ============================================================
    # Return report
    # ============================================================
    return {
        "summary_rows": summary_rows,
        "issue_dfs": issue_dfs
    }

# Other helpers
def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

def format_report(report: dict[str, Any], n: int=10, truncate: bool=False) -> None:
    """
    Display a health-check report.

    Parameters
    ----------
    report : dict
        Output from run_consistency_checks(...) or run_validity_checks(...)
    n : int
        Number of example rows to show from each issue DataFrame
    truncate : bool
        Whether Spark should truncate long values in .show()

    TBD
    """

    # Organize report into (name, count)
    summary_rows = {
        row["issue_name"]: (row["violation_count"], row['violation_rate'])
        for row in report['summary_rows']
    }

    # Show report statistics and preview df
    for issue_name, issue_df in report["issue_dfs"].items():
        issue_count, issue_rate = summary_rows.get(issue_name, (None, None))
        print_section(issue_name)
        print(f"Violation count: {issue_count}")
        print(f"Violation percentage: {issue_rate}")
        print(f"Showing first {n} rows:")
        issue_df.show(n=n, truncate=truncate)

def _rate(count_value: int, denominator_value: int) -> float:
    """
    Safely compute a rate.
    Returns None if denominator is zero.
    """
    if denominator_value in (0, None):
        return float('inf')
    return count_value / denominator_value

def _register_issue(issue_name: str, issue_df: SparkDataFrame, summary_rows: list[dict[str, Any]], issue_dfs: dict[str, SparkDataFrame], row_count: int, issue_content=None) -> tuple[SummaryType, IssueDfType]:    
    # Update issue df
    issue_dfs[issue_name] = issue_df
    violation_count = issue_df.count()

    # Define issue content
    if not issue_content:
        issue_content = {
            "issue_name": issue_name,
            "violation_count": violation_count,
            "violation_rate": _rate(violation_count, row_count),
        }

    # update summary df
    summary_rows.append(issue_content)
    return (summary_rows, issue_dfs)



    # Register report
    issue_content = {
        "issue_name": "combo_dup",
        "key_cols": DUP_KEY_COLS,
        "duplicate_key_groups": dup_key_group_count,
        "duplicate_key_rows": dup_key_row_count,
    }
    summary_rows, issue_dfs = _register_issue(
        "combo_dup", 
        combo_dup_df,
        summary_rows, 
        issue_dfs, 
        row_count,
        issue_content
    )