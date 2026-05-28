# -----------------------------
# Import Modules
# -----------------------------

from typing import Any, Iterable, TypeAlias

import numpy as np
import pandas as pd

from data_health_audit import (
    NUMERIC_COLS, 
    CATEGORICAL_COLS, 
    DUP_KEY_COLS
)
from data_prep import (
    REQUIRED_CORE_COLS,
    TEMPORAL_COLS,
    NUMERIC_COUNT_COLS
)

# ---------------------------------------------------------------------
# Audit constants
# ---------------------------------------------------------------------
# Schema
EXPECTED_PANDAS_SCHEMA = {
    "author_steamid": "Int64",
    "appid": "Int32",
    "author_num_games_owned": "Int32",
    "author_num_reviews": "Int32",
    "author_playtime_forever": "Int32",
    "author_playtime_last_two_weeks": "Int32",
    "author_playtime_at_review": "Int32",
    "author_last_played": "Int64",
    "review": "string",
    "voted_up": "boolean",
    "votes_up": "Int32",
    "votes_funny": "Int64",
    "weighted_vote_score": "Float32",
    "comment_count": "Int32",
    "written_during_early_access": "boolean",
    "timestamp_created": "Int64",
    "timestamp_updated": "Int64",
    "language": "string",
}

# Reusable columns
OPTIONAL_COLS = {
    "language",
}

# Reusable types
SummaryRows: TypeAlias = list[dict[str, Any]]
IssueDfs: TypeAlias = dict[str, pd.DataFrame]
ReportDict: TypeAlias = dict[str, Any]

# Config Parameters
VOTES_FUNNY_ARTIFACT_THRESHOLD = 4_000_000_000
VOTES_FUNNY_MAX = 2**32 - 1

MAX_2W_MINUTES = 14 * 24 * 60
PLAYTIME_2W_NEAR_LIMIT_THRESHOLD = 0.90 * MAX_2W_MINUTES

MIN_REASONABLE_UNIX_TS = 1_000_000_000
VALID_SCORE_RANGE = (0.0, 1.0)

DEFAULT_MAX_ISSUE_ROWS = 50


# -----------------------------
# Health Audit Logic
# -----------------------------
# Inpsect the dimension & cell counts
def structure_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Inspect basic dataframe size and memory footprint.
    """

    # Count on row, columns, cell and memory
    row_count = len(df)
    column_count = len(df.columns)
    cell_count = row_count * column_count
    memory_bytes = int(df.memory_usage(deep=True).sum())

    return pd.DataFrame(
        [
            {
                "row_count": row_count,
                "column_count": column_count,
                "cell_count": cell_count,
                "memory_bytes": memory_bytes,
                "memory_mb": memory_bytes / (1024**2),
            }
        ]
    )


# Check how the data type deviate from the expected schema
def schema_audit(
    df: pd.DataFrame,
    expected_schema: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """
    Compare actual Pandas dtypes against expected project dtypes.

    This is an audit only. Do not cast here.
    Casting belongs in data_prep_pandas.py.
    """
    if expected_schema is None:
        expected_schema = EXPECTED_PANDAS_SCHEMA

    rows = []
    present_cols = set(df.columns)
    actual_dtypes = {c: str(dtype) for c, dtype in df.dtypes.items()}

    for col_name, expected_dtype_raw in expected_schema.items():
        expected_dtype = _expected_dtype_to_str(expected_dtype_raw)
        actual_dtype = actual_dtypes.get(col_name)

        rows.append(
            {
                "column_name": col_name,
                "present_in_df": col_name in present_cols,
                "is_optional": col_name in OPTIONAL_COLS,
                "expected_type": expected_dtype,
                "actual_type": actual_dtype,
                "matches_expected_family": (
                    _matches_expected_dtype_family(actual_dtype, expected_dtype)
                    if actual_dtype is not None
                    else False
                ),
            }
        )

    # Also surface unexpected extra columns.
    expected_cols = set(expected_schema.keys())
    for col_name in sorted(present_cols - expected_cols):
        rows.append(
            {
                "column_name": col_name,
                "present_in_df": True,
                "is_optional": False,
                "expected_type": None,
                "actual_type": actual_dtypes.get(col_name),
                "matches_expected_family": False,
            }
        )

    return pd.DataFrame(rows)

# Check missing rows
def null_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Count null values and null rates per column.
    """
    row_count = len(df)
    null_counts = df.isna().sum()

    report = pd.DataFrame(
        {
            "column_name": null_counts.index,
            "dtype": [str(df[c].dtype) for c in null_counts.index],
            "null_count": null_counts.values.astype("int64"),
            "non_null_count": (row_count - null_counts.values).astype("int64"),
            "null_rate": [
                _rate(int(v), row_count)
                for v in null_counts.values
            ],
        }
    )

    return (
        report
        .sort_values(["null_rate", "null_count"], ascending=[False, False])
        .reset_index(drop=True)
    )

# Check logical consistency in data
def consistency_report(df: pd.DataFrame) -> ReportDict:
    """
    Run logical cross-column and over-time consistency checks.
    """
    row_count = len(df)
    summary_rows: SummaryRows = []
    issue_dfs: IssueDfs = {}

    # 1. timestamp_created should be <= timestamp_updated.
    required = {"timestamp_created", "timestamp_updated"}
    if required.issubset(df.columns):
        created = _to_numeric(df, "timestamp_created")
        updated = _to_numeric(df, "timestamp_updated")

        mask = _as_bool_mask(
            created.notna()
            & updated.notna()
            & (created > updated)
        )

        issue_df = df.loc[
            mask,
            _safe_cols(
                df,
                [
                    "author_steamid",
                    "appid",
                    "timestamp_created",
                    "timestamp_updated",
                ],
            ),
        ].copy()

        summary_rows, issue_dfs = _register_issue(
            "timestamp_created_gt_timestamp_updated",
            issue_df,
            summary_rows,
            issue_dfs,
            row_count,
            int(mask.sum()),
        )

    # 2A. playtime_at_review should be <= playtime_forever.
    required = {"author_playtime_at_review", "author_playtime_forever"}
    if required.issubset(df.columns):
        at_review = _to_numeric(df, "author_playtime_at_review")
        forever = _to_numeric(df, "author_playtime_forever")

        mask = _as_bool_mask(
            at_review.notna()
            & forever.notna()
            & (at_review > forever)
        )

        issue_df = df.loc[
            mask,
            _safe_cols(
                df,
                [
                    "author_steamid",
                    "appid",
                    "author_playtime_at_review",
                    "author_playtime_forever",
                    "timestamp_created",
                ],
            ),
        ].copy()

        summary_rows, issue_dfs = _register_issue(
            "author_playtime_at_review_gt_author_playtime_forever",
            issue_df,
            summary_rows,
            issue_dfs,
            row_count,
            int(mask.sum()),
        )

    # 2B. last_two_weeks playtime should be <= playtime_forever.
    required = {"author_playtime_last_two_weeks", "author_playtime_forever"}
    if required.issubset(df.columns):
        two_weeks = _to_numeric(df, "author_playtime_last_two_weeks")
        forever = _to_numeric(df, "author_playtime_forever")

        mask = _as_bool_mask(
            two_weeks.notna()
            & forever.notna()
            & (two_weeks > forever)
        )

        issue_df = df.loc[
            mask,
            _safe_cols(
                df,
                [
                    "author_steamid",
                    "appid",
                    "author_playtime_last_two_weeks",
                    "author_playtime_forever",
                    "timestamp_created",
                ],
            ),
        ].copy()

        summary_rows, issue_dfs = _register_issue(
            "author_playtime_last_two_weeks_gt_author_playtime_forever",
            issue_df,
            summary_rows,
            issue_dfs,
            row_count,
            int(mask.sum()),
        )

    # 3. Users whose minimum observed author_num_reviews <= 0.
    required = {"author_steamid", "author_num_reviews"}
    if required.issubset(df.columns):
        tmp = df[["author_steamid", "author_num_reviews"]].copy()
        tmp["_author_num_reviews_num"] = pd.to_numeric(
            tmp["author_num_reviews"],
            errors="coerce",
        )

        total_users = int(tmp["author_steamid"].dropna().nunique())

        user_min_reviews = (
            tmp.dropna(subset=["author_steamid"])
            .groupby("author_steamid", dropna=False)["_author_num_reviews_num"]
            .min()
            .reset_index(name="min_author_num_reviews")
        )

        issue_df = user_min_reviews.loc[
            user_min_reviews["min_author_num_reviews"].notna()
            & (user_min_reviews["min_author_num_reviews"] <= 0)
        ].copy()

        summary_rows, issue_dfs = _register_issue(
            "users_with_min_author_num_reviews_le_0",
            issue_df,
            summary_rows,
            issue_dfs,
            denominator=total_users,
            violation_count=len(issue_df),
        )

    # 4. Lifetime playtime should not decrease over time within user-app.
    required = {
        "author_steamid",
        "appid",
        "timestamp_created",
        "author_playtime_forever",
    }
    if required.issubset(df.columns):
        issue_cols = [
            "author_steamid",
            "appid",
            "timestamp_created",
            "author_playtime_forever",
        ]

        tmp = df[issue_cols].copy()
        tmp["_timestamp_num"] = pd.to_numeric(tmp["timestamp_created"], errors="coerce")
        tmp["_playtime_forever_num"] = pd.to_numeric(
            tmp["author_playtime_forever"],
            errors="coerce",
        )

        tmp = tmp.dropna(
            subset=[
                "author_steamid",
                "appid",
                "_timestamp_num",
                "_playtime_forever_num",
            ]
        )

        tmp = tmp.sort_values(
            ["author_steamid", "appid", "_timestamp_num"],
            na_position="last",
        )

        tmp["prev_playtime_forever"] = (
            tmp.groupby(["author_steamid", "appid"], dropna=False)[
                "_playtime_forever_num"
            ]
            .shift(1)
        )

        mask = _as_bool_mask(
            tmp["prev_playtime_forever"].notna()
            & (tmp["_playtime_forever_num"] < tmp["prev_playtime_forever"])
        )

        issue_df = tmp.loc[
            mask,
            [
                "author_steamid",
                "appid",
                "timestamp_created",
                "author_playtime_forever",
                "prev_playtime_forever",
            ],
        ].copy()

        summary_rows, issue_dfs = _register_issue(
            "author_playtime_forever_decreases_over_time",
            issue_df,
            summary_rows,
            issue_dfs,
            denominator=row_count,
            violation_count=len(issue_df),
        )

    return {
        "summary_rows": summary_rows,
        "summary_df": _summary_df(summary_rows),
        "issue_dfs": issue_dfs,
    }

# Check validity/egde case in data
def validity_report(df: pd.DataFrame) -> ReportDict:
    """
    Run single-column validity checks:
    - count-like columns should not be negative
    - weighted_vote_score should be in [0, 1]
    - timestamp-like columns should be above rough Unix cutoff
    """
    row_count = len(df)
    summary_rows: SummaryRows = []
    issue_dfs: IssueDfs = {}

    # 1. Count-like columns should not be negative.
    for col_name in NUMERIC_COUNT_COLS:
        if col_name not in df.columns:
            continue

        s = _to_numeric(df, col_name)
        mask = _as_bool_mask(s.notna() & (s < 0))

        issue_df = df.loc[
            mask,
            _safe_cols(
                df,
                [
                    "author_steamid",
                    "appid",
                    col_name,
                    "timestamp_created",
                ],
            ),
        ].copy()

        summary_rows, issue_dfs = _register_issue(
            f"{col_name}_negative",
            issue_df,
            summary_rows,
            issue_dfs,
            denominator=row_count,
            violation_count=int(mask.sum()),
        )

    # 2. weighted_vote_score should be in [0, 1].
    if "weighted_vote_score" in df.columns:
        s = _to_numeric(df, "weighted_vote_score")
        low, high = VALID_SCORE_RANGE

        mask = _as_bool_mask(
            s.notna()
            & ~s.between(low, high, inclusive="both")
        )

        issue_df = df.loc[
            mask,
            _safe_cols(
                df,
                [
                    "author_steamid",
                    "appid",
                    "weighted_vote_score",
                    "timestamp_created",
                ],
            ),
        ].copy()

        summary_rows, issue_dfs = _register_issue(
            "weighted_vote_score_out_of_range",
            issue_df,
            summary_rows,
            issue_dfs,
            denominator=row_count,
            violation_count=int(mask.sum()),
        )

    # 3. Timestamp values should be after rough Steam-era cutoff.
    for col_name in TEMPORAL_COLS:
        if col_name not in df.columns:
            continue

        s = _to_numeric(df, col_name)
        mask = _as_bool_mask(
            s.notna()
            & (s <= MIN_REASONABLE_UNIX_TS)
        )

        issue_df = df.loc[
            mask,
            _safe_cols(
                df,
                [
                    "author_steamid",
                    "appid",
                    col_name,
                    "timestamp_created",
                ],
            ),
        ].copy()

        summary_rows, issue_dfs = _register_issue(
            f"{col_name}_before_reasonable_unix_cutoff",
            issue_df,
            summary_rows,
            issue_dfs,
            denominator=row_count,
            violation_count=int(mask.sum()),
        )

    return {
        "summary_rows": summary_rows,
        "summary_df": _summary_df(summary_rows),
        "issue_dfs": issue_dfs,
    }

# Check for statistical outlier & anomaly
def anomaly_report(df: pd.DataFrame) -> ReportDict:
    """
    Build anomaly report for suspicious-but-not-always-invalid values.

    Covered:
    1. numeric summary statistics
    2. author_playtime_last_two_weeks near physical max
    3. author_playtime_last_two_weeks above physical max
    4. votes_funny uint32-style artifact zone
    5. votes_funny exact uint32 max
    """
    row_count = len(df)
    summary_rows: SummaryRows = []
    issue_dfs: IssueDfs = {}

    # 1. Numeric describe table.
    numeric_cols = _safe_cols(df, NUMERIC_COLS)

    if numeric_cols:
        numeric_describe_df = (
            df[numeric_cols]
            .apply(pd.to_numeric, errors="coerce")
            .describe(
                percentiles=[
                    0.01,
                    0.05,
                    0.25,
                    0.50,
                    0.75,
                    0.95,
                    0.99,
                ]
            )
            .T
            .reset_index()
            .rename(columns={"index": "column_name"})
        )
    else:
        numeric_describe_df = pd.DataFrame()

    # 2A. playtime_last_two_weeks >= 90% of physical 14-day max.
    if "author_playtime_last_two_weeks" in df.columns:
        s = _to_numeric(df, "author_playtime_last_two_weeks")

        mask = _as_bool_mask(
            s.notna()
            & (s >= PLAYTIME_2W_NEAR_LIMIT_THRESHOLD)
        )

        issue_df = df.loc[
            mask,
            _safe_cols(
                df,
                [
                    "author_steamid",
                    "appid",
                    "author_playtime_last_two_weeks",
                    "author_playtime_forever",
                    "timestamp_created",
                ],
            ),
        ].copy()

        if "author_playtime_last_two_weeks" in issue_df.columns:
            issue_df = issue_df.sort_values(
                "author_playtime_last_two_weeks",
                ascending=False,
                na_position="last",
            )

        summary_rows, issue_dfs = _register_issue(
            "playtime_2w_near_limit",
            issue_df,
            summary_rows,
            issue_dfs,
            denominator=row_count,
            violation_count=int(mask.sum()),
        )

        # 2B. playtime_last_two_weeks > physical max.
        mask = _as_bool_mask(
            s.notna()
            & (s > MAX_2W_MINUTES)
        )

        issue_df = df.loc[
            mask,
            _safe_cols(
                df,
                [
                    "author_steamid",
                    "appid",
                    "author_playtime_last_two_weeks",
                    "author_playtime_forever",
                    "timestamp_created",
                ],
            ),
        ].copy()

        if "author_playtime_last_two_weeks" in issue_df.columns:
            issue_df = issue_df.sort_values(
                "author_playtime_last_two_weeks",
                ascending=False,
                na_position="last",
            )

        summary_rows, issue_dfs = _register_issue(
            "playtime_2w_exceeds_limit",
            issue_df,
            summary_rows,
            issue_dfs,
            denominator=row_count,
            violation_count=int(mask.sum()),
        )

    # 3. votes_funny artifact checks.
    if "votes_funny" in df.columns:
        s = _to_numeric(df, "votes_funny")

        issue_cols = _safe_cols(
            df,
            [
                "author_steamid",
                "appid",
                "votes_funny",
                "votes_up",
                "weighted_vote_score",
                "comment_count",
                "timestamp_created",
            ],
        )

        # 3A. broad artifact zone.
        mask = _as_bool_mask(
            s.notna()
            & (s >= VOTES_FUNNY_ARTIFACT_THRESHOLD)
        )

        issue_df = df.loc[mask, issue_cols].copy()
        if "votes_funny" in issue_df.columns:
            issue_df = issue_df.sort_values(
                "votes_funny",
                ascending=False,
                na_position="last",
            )

        summary_rows, issue_dfs = _register_issue(
            "votes_funny_is_uint32_artifact",
            issue_df,
            summary_rows,
            issue_dfs,
            denominator=row_count,
            violation_count=int(mask.sum()),
        )

        # 3B. near-exact uint32 artifact range, excluding exact max.
        mask = _as_bool_mask(
            s.notna()
            & (s >= VOTES_FUNNY_ARTIFACT_THRESHOLD)
            & (s < VOTES_FUNNY_MAX)
        )

        issue_df = df.loc[mask, issue_cols].copy()
        if "votes_funny" in issue_df.columns:
            issue_df = issue_df.sort_values(
                "votes_funny",
                ascending=False,
                na_position="last",
            )

        summary_rows, issue_dfs = _register_issue(
            "votes_funny_near_exact_uint32_artifact_max",
            issue_df,
            summary_rows,
            issue_dfs,
            denominator=row_count,
            violation_count=int(mask.sum()),
        )

        # 3C. exact uint32 max.
        mask = _as_bool_mask(
            s.notna()
            & (s == VOTES_FUNNY_MAX)
        )

        issue_df = df.loc[mask, issue_cols].copy()
        if "votes_funny" in issue_df.columns:
            issue_df = issue_df.sort_values(
                "votes_funny",
                ascending=False,
                na_position="last",
            )

        summary_rows, issue_dfs = _register_issue(
            "votes_funny_exact_uint32_max",
            issue_df,
            summary_rows,
            issue_dfs,
            denominator=row_count,
            violation_count=int(mask.sum()),
        )

        # 3D. Reference row: largest non-artifact votes_funny below threshold.
        non_artifact_mask = _as_bool_mask(
            s.notna()
            & (s < VOTES_FUNNY_ARTIFACT_THRESHOLD)
        )

        if non_artifact_mask.any():
            idx = s.loc[non_artifact_mask].idxmax()
            issue_dfs["largest_non_artifact_votes_funny_below_threshold"] = (
                df.loc[[idx], issue_cols]
                .reset_index(drop=True)
            )
        else:
            issue_dfs["largest_non_artifact_votes_funny_below_threshold"] = (
                pd.DataFrame(columns=issue_cols)
            )

    return {
        "summary_rows": summary_rows,
        "summary_df": _summary_df(summary_rows),
        "issue_dfs": issue_dfs,
        "numeric_describe_df": numeric_describe_df,
    }

# ---------------------------------------------------------------------
# 4. Duplicate report
# ---------------------------------------------------------------------

def duplicate_report(
    df: pd.DataFrame,
    dup_key_cols: Iterable[str] = DUP_KEY_COLS,
) -> ReportDict:
    """
    Check:
    1. exact duplicate rows
    2. duplicate review keys using author_steamid + appid + timestamp_created
    """
    row_count = len(df)
    summary_rows: SummaryRows = []
    issue_dfs: IssueDfs = {}

    # 1. Exact duplicate rows.
    exact_dup_mask = _as_bool_mask(df.duplicated(keep=False))
    exact_dup_df = df.loc[exact_dup_mask].copy()

    summary_rows, issue_dfs = _register_issue(
        issue_name="exact_duplicate_rows",
        issue_df=exact_dup_df,
        summary_rows=summary_rows,
        issue_dfs=issue_dfs,
        denominator=row_count,
        violation_count=int(exact_dup_mask.sum()),
    )

    # 2. Duplicate composite review keys.
    dup_key_cols = list(dup_key_cols)
    present_key_cols = _safe_cols(df, dup_key_cols)

    if len(present_key_cols) == len(dup_key_cols):
        key_dup_mask = _as_bool_mask(df.duplicated(subset=present_key_cols, keep=False))
        issue_cols = _safe_cols(
            df,
            [
                "author_steamid",
                "appid",
                "timestamp_created",
                "timestamp_updated",
                "review",
                "voted_up",
            ],
        )

        key_dup_df = df.loc[key_dup_mask, issue_cols].copy()

        sort_cols = present_key_cols.copy()
        if "timestamp_updated" in key_dup_df.columns:
            sort_cols.append("timestamp_updated")

        if sort_cols:
            key_dup_df = key_dup_df.sort_values(sort_cols, na_position="last")

        summary_rows, issue_dfs = _register_issue(
            issue_name="duplicate_review_key_rows",
            issue_df=key_dup_df,
            summary_rows=summary_rows,
            issue_dfs=issue_dfs,
            denominator=row_count,
            violation_count=int(key_dup_mask.sum()),
        )

        duplicate_key_groups = (
            df.loc[key_dup_mask]
            .groupby(present_key_cols, dropna=False)
            .size()
            .reset_index(name="group_size")
            .sort_values("group_size", ascending=False)
            .head(DEFAULT_MAX_ISSUE_ROWS)
            .reset_index(drop=True)
        )
        issue_dfs["duplicate_review_key_groups"] = duplicate_key_groups

    else:
        missing = sorted(set(dup_key_cols) - set(present_key_cols))
        issue_dfs["duplicate_review_key_rows"] = pd.DataFrame(
            {"missing_required_key_columns": missing}
        )

        summary_rows.append(
            {
                "issue_name": "duplicate_review_key_rows_skipped_missing_columns",
                "violation_count": 0,
                "denominator": row_count,
                "violation_rate": 0.0,
                "stored_issue_rows": 0,
            }
        )

    return {
        "summary_rows": summary_rows,
        "summary_df": _summary_df(summary_rows),
        "issue_dfs": issue_dfs,
    }

# ---------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------

def _rate(count: int, denominator: int | float | None) -> float:
    if denominator is None or denominator == 0:
        return np.nan
    return float(count) / float(denominator)


def _safe_cols(df: pd.DataFrame, cols: Iterable[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


def _to_numeric(df: pd.DataFrame, col_name: str) -> pd.Series:
    if col_name not in df.columns:
        return pd.Series(np.nan, index=df.index)
    return pd.to_numeric(df[col_name], errors="coerce")


def _as_bool_mask(mask: pd.Series) -> pd.Series:
    return mask.fillna(False).astype(bool)


def _expected_dtype_to_str(dtype: Any) -> str:
    """
    Accept either Pandas-style dtype strings or Spark DataType objects.
    This lets you pass a Spark BASE_SCHEMA later if you want.
    """
    if hasattr(dtype, "simpleString"):
        spark_type = dtype.simpleString().lower()
        spark_to_pandas = {
            "bigint": "Int64",
            "long": "Int64",
            "int": "Int32",
            "integer": "Int32",
            "float": "Float32",
            "double": "Float64",
            "string": "string",
            "boolean": "boolean",
        }
        return spark_to_pandas.get(spark_type, spark_type)

    return str(dtype)


def _matches_expected_dtype_family(actual_dtype: str, expected_dtype: str) -> bool:
    actual = str(actual_dtype).lower()
    expected = str(expected_dtype).lower()

    if expected in {"int32", "int64"}:
        return actual == expected

    if expected in {"float32", "float64"}:
        return actual in {"float32", "float64"}

    if expected == "boolean":
        return actual in {"bool", "boolean"}

    if expected == "string":
        return actual in {"string", "object"}

    return actual == expected


def _register_issue(
    issue_name: str,
    issue_df: pd.DataFrame,
    summary_rows: SummaryRows,
    issue_dfs: IssueDfs,
    denominator: int | float | None,
    violation_count: int | None = None,
    max_issue_rows: int = DEFAULT_MAX_ISSUE_ROWS,
) -> tuple[SummaryRows, IssueDfs]:
    """
    Register one issue in report style.

    Important Pandas difference from Spark:
    Spark issue_dfs are lazy. Pandas issue_dfs are eager in memory.
    Therefore, this stores only the first max_issue_rows examples but
    still records the full violation_count.
    """
    if violation_count is None:
        violation_count = len(issue_df)

    summary_rows.append(
        {
            "issue_name": issue_name,
            "violation_count": int(violation_count),
            "denominator": denominator,
            "violation_rate": _rate(int(violation_count), denominator),
            "stored_issue_rows": int(min(len(issue_df), max_issue_rows)),
        }
    )

    issue_dfs[issue_name] = issue_df.head(max_issue_rows).reset_index(drop=True)
    return summary_rows, issue_dfs


def _empty_issue_df() -> pd.DataFrame:
    return pd.DataFrame()


def _summary_df(summary_rows: SummaryRows) -> pd.DataFrame:
    if not summary_rows:
        return pd.DataFrame(
            columns=[
                "issue_name",
                "violation_count",
                "denominator",
                "violation_rate",
                "stored_issue_rows",
            ]
        )

    return (
        pd.DataFrame(summary_rows)
        .sort_values(["violation_count", "violation_rate"], ascending=[False, False])
        .reset_index(drop=True)
    )
