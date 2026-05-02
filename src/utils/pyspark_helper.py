from pyspark.sql import (
    SparkSession, 
    DataFrame, 
    functions as F
)
from pyspark.sql.types import (
    LongType, IntegerType,
    FloatType, StringType, BooleanType
)

import seaborn as sns
import matplotlib.pyplot as plt

BASE_SCHEMA = {
    "author_steamid": LongType(),
    "appid": IntegerType(),
    "author_num_games_owned": IntegerType(),
    "author_num_reviews": IntegerType(),
    "author_playtime_forever": IntegerType(),
    "author_playtime_last_two_weeks": IntegerType(),
    "author_playtime_at_review": IntegerType(),
    "author_last_played": LongType(),
    "review":StringType(),
    "voted_up": BooleanType(),
    "votes_up": IntegerType(),
    "votes_funny": LongType(),
    "weighted_vote_score": FloatType(),
    "comment_count": IntegerType(),
    "written_during_early_access": BooleanType(),
    "timestamp_created": LongType(),
    "timestamp_updated": LongType(),
    # Your sampled Pandas PreEDA had this column.
    # We treat it as optional because your Spark ingestion schema does not include it.
    "language": StringType(),
}

SPARK_CONFIGS = {
    # Resources
    "spark.driver.memory": "10g",
    "spark.driver.cores": "1",
    "spark.executor.instances": "4",
    "spark.executor.cores": "2",
    "spark.executor.memory": "38g",

    # Parallelism
    "spark.sql.shuffle.partitions": "32",
    "spark.default.parallelism": "32",
    "spark.driver.maxResultSize": "4g",
}

def create_spark_session(app_name: str, extra_configs: dict | None = None):
    """
    Create a SparkSession using shared default configs.

    Args:
        app_name: Name shown in Spark UI / logs.
        extra_configs: Optional per-script overrides.

    Returns:
        SparkSession
    """
    configs = SPARK_CONFIGS.copy()

    if extra_configs:
        configs.update(extra_configs)

    builder = SparkSession.builder.appName(app_name)

    for key, value in configs.items():
        builder = builder.config(key, value)

    return builder.getOrCreate()

def memory_count(df: DataFrame, include_row_count: bool=False) -> None:
    """
    Estimate row count and memory footprint of a Spark DataFrame.

    Args:
        df: Spark DataFrame to analyze
        include_row_count: Whether to display the numbers of row

    Prints:
        - Total number of rows in the DataFrame (Conditional) 
        - Estimated total memory usage in GB
    """

    if include_row_count:
        # How many df rows do we have?
        row_counts = df.count()
        print(f"Total row counts: {row_counts} rows")
    
    # How much does df occupy in memory?
    sample_fraction = 0.001
    sample_size_in_bytes = (
        df
        .sample(fraction=sample_fraction)
        .toPandas()
        .memory_usage(deep=True)
        .sum()
    ) 
    total_size_in_gb = sample_size_in_bytes / (sample_fraction * (1024**3))
    print(f"Total estimated size: {total_size_in_gb:.2f} GB")

def plot_bar_chart(df, groupby_col, x_label, title, has_hue=True) -> None:
    """
    Plot a horizontal bar chart of the top N categories for a Spark DataFrame column.

    Args:
        df: Spark DataFrame
        groupby_col: Column name (string) to group by
        x_label: Label for the x-axis
        title: Plot title

    Notes:
        - Counts are annotated in millions (M) by default
    """
    
    # --- Data ---
    dist_pd = (
        df
        # Groupby + Agg(count) + Sort
        .groupBy(groupby_col)
        .count()
        .orderBy(F.desc('count'))
        .toPandas()
        .loc[lambda temp_df: temp_df[groupby_col].notna(), :]
        .assign(**{
            groupby_col: lambda df: df[groupby_col].astype('category')
        })
        .sort_values(by='count', ascending=False)
    )
    
    # --- Plot ---
    fig, ax = plt.subplots(figsize=(15, 6))
    sns.barplot(
        data=dist_pd,
        x='count',
        y=groupby_col,
        hue=groupby_col if has_hue else None,
        legend=False,
        palette='Blues_r' if has_hue else None,
        edgecolor='white',
        ax=ax,
        order=dist_pd[groupby_col].tolist(),
        hue_order=dist_pd[groupby_col].tolist()
    )
    # Edit text on categories
    for bar in ax.patches:
        w = bar.get_width()
        ax.text(
            w + 50_000, bar.get_y() + bar.get_height() / 2,
            f'{w/1_000_000:.2f}M',
            va='center', ha='left', fontsize=9, color='#333'
        )
    # Annotation
    ax.set_xlabel(x_label, fontsize=11)
    ax.set_title(
        title, 
        fontsize=14, 
        fontweight='bold', 
        pad=15
    )
    plt.show()

# def show_and_write_to_csv(df: DataFrame, path: str, name: str, n: int = 20, truncate: bool = False, save_reports: bool = False) -> None:
#     print(f"\n===== {name} =====")
#     df.show(n=n, truncate=truncate)
#     if save_reports:
#         (
#             df.write
#             .mode("overwrite")
#             .option("header", "true")
#             .csv(f"{path}/{name}")
#         )

# def show_and_write_to_json(payload: dict, path: str, name: str, save_reports: bool = False) -> None:
#     print(f"\n===== {name} =====")
#     print(json.dumps(payload, indent=2, default=str))
#     if save_reports:
#         local_stub = Path("/mnt/data") / f"{name}.json"
#         local_stub.write_text(json.dumps(payload, indent=2, default=str))

# def save_parquet(df: DataFrame, root: str, name: str) -> None:
#     (
#         df.write
#         .mode("overwrite")
#         .parquet(f"{root}/{name}")
#     )