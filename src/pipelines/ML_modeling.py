# =============================================================================
# FUTURE PLAN (not yet implemented -- review before acting)
# -----------------------------------------------------------------------------
# This module currently bundles the whole ML workflow. If/when it grows further,
# consider splitting it by responsibility into separate files under
# src/pipelines/. Suggested layout and dependency direction (top depends on
# nothing internal; each lower line may import the ones above it -- no cycles):
#
#   ml_common.py
#       Shared constants (FEATURE_COL, LABEL_COL, DEFAULT_METRICS,
#       MODEL_DISPLAY_NAMES, DEFAULT_MODEL_ORDER, SEED, the SparkClassifier type)
#       and private helpers (_build_evaluator, _model_display_name,
#       _apply_dark_axes_style, _prepare_model_frame_for_xgb, _metric_value,
#       _param_map_to_dict, _cv_results_to_df).
#
#   ml_modeling.py   (-> ml_common)
#       Definition / fit / transform / evaluate: build_models,
#       fit_transform_model, evaluate_model, evaluate_split.
#
#   ml_metric.py     (-> ml_common)
#       Metric generation / organization: metric_dict_to_rows, rows_to_pandas_df,
#       build_presentation_metrics, build_model_comparison_table,
#       format_model_comparison_table, build_roc_curve_table,
#       build_confusion_matrix_table, build_feature_importance_table.
#
#   ml_metric_visualization.py   (-> ml_common, ml_metric)
#       All plot_* functions.
#
#   ml_tuning.py     (-> ml_common, ml_modeling)
#       Hyperparameter tuning: DEFAULT_PARAM_GRIDS, build_param_grid,
#       cross_validate_model.
#
#   ml_io.py         (-> ml_common)
#       Model persistence: MODEL_LOADER_CLASSES, save_model, load_model
#       (writes/reads fitted models under ProjectPaths.models_root, e.g.
#       models/xgb/). Used by 7_ML_modeling.ipynb and 8_ML_tuning.ipynb.
#
#   Orchestration (fit_transform_evaluate_models, build_model_report_assets)
#       sits above modeling + metric + visualization, so it belongs either in a
#       dedicated ml_pipeline.py or at the top of ml_modeling.py.
#
# IMPORTANT: to preserve the uniform `import src.pipelines.ML_modeling as ml;
# ml.X(...)` usage in the notebooks, keep ML_modeling.py as a thin FACADE that
# re-exports the public names from the submodules above. That keeps notebooks 7
# and 8 unchanged while the internals become organized by responsibility.
# =============================================================================

# -----------------------------
# Import Modules
# -----------------------------
# Spark
from pyspark import StorageLevel
from pyspark.sql import SparkSession, DataFrame, functions as F
from pyspark.ml.functions import vector_to_array

# ML
from pyspark.ml.classification import (
    LogisticRegression,
    DecisionTreeClassifier,
    RandomForestClassifier,
    LinearSVC,
    LogisticRegressionModel,
    DecisionTreeClassificationModel,
    RandomForestClassificationModel,
    LinearSVCModel,
)
from xgboost.spark import SparkXGBClassifier, SparkXGBClassifierModel
from pyspark.ml.evaluation import (
    BinaryClassificationEvaluator,
    MulticlassClassificationEvaluator,
)
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.mllib.evaluation import BinaryClassificationMetrics

# Others
from pathlib import Path
from typing import TypeAlias, Optional, Any
import time

import pandas as pd
import matplotlib.pyplot as plt


# -----------------------------
# ML Constants
# -----------------------------
# Reusable columns
FEATURE_COL = "finalized_features"
LABEL_COL = "churn"
PREDICTION_COL = "prediction"
RAW_PREDICTION_COL = "rawPrediction"
PROBABILITY_COL = "probability"

# Reusable type
SparkClassifier: TypeAlias = (
    LogisticRegression
    | DecisionTreeClassifier
    | RandomForestClassifier
    | LinearSVC
    | SparkXGBClassifier
)

# Reusable metric groups
DEFAULT_METRICS = [
    "areaUnderROC",
    "areaUnderPR",
    "f1",
    "weightedPrecision",
    "weightedRecall",
    "accuracy",
]

BINARY_METRICS = {
    "areaUnderROC", 
    "areaUnderPR"
}

MULTICLASS_METRICS = {
    "f1",
    "weightedPrecision",
    "weightedRecall",
    "accuracy",
}

MODEL_COMPARISON_METRICS = [
    "areaUnderROC",
    "f1",
    "accuracy",
    "weightedPrecision",
    "weightedRecall",
]

MODEL_TRAIN_TEST_COMPARISON_METRICS = [
    "areaUnderROC",
    "accuracy",
    "f1",
]

# Friendly names used in tables and figures.
MODEL_DISPLAY_NAMES = {
    "log_reg": "Logistic Regression",
    "decision_tree": "Decision Tree",
    "random_forest": "Random Forest",
    "xgb": "XGBoost",
    "svm": "SVM",
}

METRIC_DISPLAY_NAMES = {
    "areaUnderROC": "AUC-ROC",
    "areaUnderPR": "AUC-PR",
    "f1": "F1",
    "weightedPrecision": "Precision",
    "weightedRecall": "Recall",
    "accuracy": "Accuracy",
}

DEFAULT_MODEL_ORDER = [
    "log_reg",
    "decision_tree",
    "random_forest",
    "xgb",
    "svm",
]

# Loader class for each model name, used by load_model() to read a saved model
# back with the correct Spark type. Keys match build_models().
MODEL_LOADER_CLASSES: dict[str, Any] = {
    "log_reg": LogisticRegressionModel,
    "decision_tree": DecisionTreeClassificationModel,
    "random_forest": RandomForestClassificationModel,
    "svm": LinearSVCModel,
    "xgb": SparkXGBClassifierModel,
}

# Random Seed
SEED = 42

# Default hyperparameter search grids used by cross_validate_model(). Each entry
# maps a model name to a {param_name: [values]} spec. The param names match the
# Spark ML / SparkXGBClassifier params set in build_models(), so the grids tune
# the same knobs as the baseline estimators. Override per-call by passing
# param_grid=... to cross_validate_model().
DEFAULT_PARAM_GRIDS: dict[str, dict[str, list[Any]]] = {
    "log_reg": {
        "regParam": [0.01, 0.1],
        "elasticNetParam": [0.0, 0.5],
    },
    "decision_tree": {
        "maxDepth": [5, 8, 12],
        "minInstancesPerNode": [1, 5, 10],
    },
    "random_forest": {
        "numTrees": [50, 100],
        "maxDepth": [8, 12],
    },
    "svm": {
        "regParam": [0.01, 0.1],
        "maxIter": [50, 100],
    },
    "xgb": {
        "max_depth": [4, 6, 8],
        "learning_rate": [0.05, 0.1],
    },
}


# -----------------------------
# XGBoost Config
# -----------------------------
def get_spark_resources(
    spark: SparkSession
) -> dict[str, int]:
    conf = spark.sparkContext.getConf()

    num_executors: int = int(conf.get("spark.executor.instances", "1"))
    executor_cores: int = int(conf.get("spark.executor.cores", "1"))
    total_cores: int = num_executors * executor_cores

    return {
        "num_executors": num_executors,
        "executor_cores": executor_cores,
        "total_cores": total_cores,
    }


# ----------------------------------
# Model Pipeline (Definition, Fit_Transform, Evaluation)
# ----------------------------------
def build_models(
    spark: SparkSession,
    mode: str = "EXPANSE"
) -> dict[str, SparkClassifier]:
    total_cores = 1

    if mode.upper() == "EXPANSE":
        total_cores = get_spark_resources(spark)["total_cores"]
        print(f"total_cores has {total_cores}")
    elif mode.upper() == "COLAB":
        total_cores = 1
    elif mode.upper() == "LOCAL":
        total_cores = 7
    else:
        raise ValueError("Invalid mode. Accepted values are: 'EXPANSE', 'COLAB', 'LOCAL'.")

    return {
        "log_reg": LogisticRegression(
            featuresCol=FEATURE_COL,
            labelCol=LABEL_COL,
            predictionCol=PREDICTION_COL,
            rawPredictionCol=RAW_PREDICTION_COL,
            probabilityCol=PROBABILITY_COL,

            # Baseline params
            # Safer than relying on a low default if convergence is slow.
            maxIter=50,
            regParam=0.0,
            elasticNetParam=0.0,
            standardization=True,
        ),

        "decision_tree": DecisionTreeClassifier(
            featuresCol=FEATURE_COL,
            labelCol=LABEL_COL,
            predictionCol=PREDICTION_COL,
            rawPredictionCol=RAW_PREDICTION_COL,
            probabilityCol=PROBABILITY_COL,

            # Baseline params
            maxDepth=8,
            minInstancesPerNode=5,
            seed=SEED,
        ),

        "random_forest": RandomForestClassifier(
            featuresCol=FEATURE_COL,
            labelCol=LABEL_COL,
            predictionCol=PREDICTION_COL,
            rawPredictionCol=RAW_PREDICTION_COL,
            probabilityCol=PROBABILITY_COL,

            # Baseline params
            numTrees=50,
            maxDepth=8,
            minInstancesPerNode=5,
            featureSubsetStrategy="sqrt",
            seed=SEED,
        ),

        "svm": LinearSVC(
            featuresCol=FEATURE_COL,
            labelCol=LABEL_COL,
            predictionCol=PREDICTION_COL,
            rawPredictionCol=RAW_PREDICTION_COL,

            # Baseline params
            maxIter=50,
            regParam=0.1,
            standardization=True,
        ),

        "xgb": SparkXGBClassifier(
            features_col=FEATURE_COL,
            label_col=LABEL_COL,
            prediction_col=PREDICTION_COL,
            raw_prediction_col=RAW_PREDICTION_COL,
            probability_col=PROBABILITY_COL,

            # Baseline params
            num_workers=total_cores,
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            seed=SEED,
        ),
    }

def fit_transform_model(
    model_name: str,
    train_final_df: DataFrame,
    test_final_df: DataFrame,
    spark: SparkSession,
    cache: bool = False,
    mode: str = "EXPANSE",
) -> tuple[Any, DataFrame, DataFrame]:
    """
    Fit one Spark ML model and return the fitted model plus train/test predictions.
    """

    models = build_models(spark, mode=mode)
    if model_name not in models:
        raise ValueError(
            f"Model name not found: {model_name}. "
            f"Available models: {sorted(models)}"
        )

    model = models[model_name]

    fitted = model.fit(train_final_df)
    train_pred_df = fitted.transform(train_final_df)
    test_pred_df = fitted.transform(test_final_df)

    if cache:
        train_pred_df = train_pred_df.persist(StorageLevel.MEMORY_AND_DISK)
        test_pred_df = test_pred_df.persist(StorageLevel.MEMORY_AND_DISK)

        # Force materialization so later evaluators do not refit/recompute repeatedly.
        train_pred_df.count()
        test_pred_df.count()

    return fitted, train_pred_df, test_pred_df

def evaluate_model(
    model_name: str,
    train_pred_df: DataFrame,
    test_pred_df: DataFrame,
    label_col: str = LABEL_COL,
    prediction_col: str = PREDICTION_COL,
    raw_prediction_col: str = RAW_PREDICTION_COL,
    metrics: Optional[list[str]] = None,
    verbose: bool = True,
    unpersist: bool = False,
) -> dict[str, dict[str, float]]:
    """
    Evaluate a binary classification model on train and validation/test data.

    BinaryClassificationEvaluator metrics:
        - areaUnderROC
        - areaUnderPR

    MulticlassClassificationEvaluator metrics:
        - f1
        - weightedPrecision
        - weightedRecall
        - accuracy

    Notes
    -----
    This function returns a nested dictionary:

        {
            "areaUnderROC": {"train": 0.82, "test": 0.81},
            ...
        }

    Set ``unpersist=True`` only when this function owns the prediction DataFrames.
    In notebooks, it is usually safer to unpersist outside this function after
    plots/tables are complete.
    """

    if metrics is None:
        metrics = DEFAULT_METRICS

    unsupported = set(metrics) - (BINARY_METRICS | MULTICLASS_METRICS)
    if unsupported:
        raise ValueError(
            f"Unsupported metrics: {sorted(unsupported)}. "
            f"Supported metrics are: {sorted(BINARY_METRICS | MULTICLASS_METRICS)}"
        )

    metric_data: dict[str, dict[str, float]] = {}

    for metric in metrics:
        evaluator = _build_evaluator(
            metric=metric,
            label_col=label_col,
            prediction_col=prediction_col,
            raw_prediction_col=raw_prediction_col,
        )

        train_score = float(evaluator.evaluate(train_pred_df))
        test_score = float(evaluator.evaluate(test_pred_df))

        if verbose:
            print(f"{model_name} Train {metric}: {train_score:.4f}")
            print(f"{model_name} Test {metric}: {test_score:.4f}")
            print()

        metric_data[metric] = {
            "train": train_score,
            "test": test_score,
        }

    if unpersist:
        train_pred_df.unpersist()
        test_pred_df.unpersist()

    return metric_data

def evaluate_split(
    model_name: str,
    pred_df: DataFrame,
    split_name: str = "Test",
    label_col: str = LABEL_COL,
    prediction_col: str = PREDICTION_COL,
    raw_prediction_col: str = RAW_PREDICTION_COL,
    metrics: Optional[list[str]] = None,
    verbose: bool = True,
) -> dict[str, float]:
    """
    Evaluate one prediction DataFrame (a single split) and return flat scores.

    This is the single-split companion to ``evaluate_model`` (which scores train
    and test together). It is handy after hyperparameter tuning, where the tuned
    ``bestModel`` is transformed on one held-out split:

        {"areaUnderROC": 0.864, "f1": 0.973, ...}
    """

    if metrics is None:
        metrics = DEFAULT_METRICS

    unsupported = set(metrics) - (BINARY_METRICS | MULTICLASS_METRICS)
    if unsupported:
        raise ValueError(
            f"Unsupported metrics: {sorted(unsupported)}. "
            f"Supported metrics are: {sorted(BINARY_METRICS | MULTICLASS_METRICS)}"
        )

    scores: dict[str, float] = {}
    for metric in metrics:
        evaluator = _build_evaluator(
            metric=metric,
            label_col=label_col,
            prediction_col=prediction_col,
            raw_prediction_col=raw_prediction_col,
        )
        score = float(evaluator.evaluate(pred_df))

        if verbose:
            print(f"{model_name} {split_name} {metric}: {score:.4f}")

        scores[metric] = score

    return scores


# -------------------------------------
# Model Metric Organization
# -------------------------------------
def metric_dict_to_rows(
    model_name: str,
    metric_dict: dict[str, dict[str, float]],
    train_time_sec: Optional[float] = None,
) -> list[dict[str, float | str | None]]:
    """
    Convert one model's nested metric dictionary into row records.

    ``train_time_sec`` is repeated on each metric row so the long-form table can
    still be pivoted into a dashboard/report table later.
    """

    rows = []
    for metric_name, split_scores in metric_dict.items():
        train_score = float(split_scores["train"])
        test_score = float(split_scores["test"])
        rows.append({
            "model": model_name,
            "metric": metric_name,
            "train": train_score,
            "test": test_score,
            "gap_train_minus_test": train_score - test_score,
            "train_time_sec": train_time_sec,
        })

    return rows

def rows_to_pandas_df(
    metric_rows: list[dict[str, Any]],
):
    """
    Build the long-form Pandas metric table used by plotting/reporting helpers.
    """

    import pandas as pd

    columns = [
        "model",
        "metric",
        "train",
        "test",
        "gap_train_minus_test",
        "train_time_sec",
    ]
    return pd.DataFrame(metric_rows, columns=columns)

def build_presentation_metrics(
    metrics_df,
    split: str = "test",
):
    """
    Convert long-form metrics into a wide presentation table.

    Example output columns:
        model, accuracy, areaUnderPR, areaUnderROC, f1, weightedPrecision, ...
    """

    required_cols = {"model", "metric", split}
    missing = required_cols - set(metrics_df.columns)
    if missing:
        raise ValueError(f"metrics_df is missing required columns: {sorted(missing)}")

    return (
        metrics_df
        .pivot(index="model", columns="metric", values=split)
        .reset_index()
    )

def build_model_comparison_table(
    metrics_df: pd.DataFrame,
    model_order: Optional[list[str]] = None,
    split: str = "test",
    include_display_name: bool = True,
) -> pd.DataFrame:
    """
    Build the model-comparison table shown in the dashboard mockups.

    Output columns are numeric by default so the table can still be sorted,
    styled, exported, or reused for charts:

    - model
    - model_display
    - auc_roc
    - auc_pr
    - f1
    - accuracy
    - train_time_sec
    - auc_gap_train_minus_test
    - is_best_auc

    ``auc_gap_train_minus_test`` follows your note in the PNG: train AUC -
    validation/test AUC. Negative values mean validation/test slightly
    outperformed train.
    """

    required_cols = {"model", "metric", "train", split}
    missing = required_cols - set(metrics_df.columns)
    if missing:
        raise ValueError(f"metrics_df is missing required columns: {sorted(missing)}")

    wide_test = (
        metrics_df
        .pivot(index="model", columns="metric", values=split)
        .reset_index()
    )
    wide_train = (
        metrics_df
        .pivot(index="model", columns="metric", values="train")
        .reset_index()
    )

    table = pd.DataFrame({
        "model": wide_test["model"],
        "auc_roc": _metric_value(wide_test, "areaUnderROC"),
        "auc_pr": _metric_value(wide_test, "areaUnderPR"),
        "f1": _metric_value(wide_test, "f1"),
        "accuracy": _metric_value(wide_test, "accuracy"),
    })

    if "areaUnderROC" in wide_train.columns and "areaUnderROC" in wide_test.columns:
        table["auc_gap_train_minus_test"] = wide_train["areaUnderROC"] - wide_test["areaUnderROC"]
    else:
        table["auc_gap_train_minus_test"] = float("nan")

    if "train_time_sec" in metrics_df.columns:
        train_time = (
            metrics_df[["model", "train_time_sec"]]
            .dropna(subset=["train_time_sec"])
            .drop_duplicates(subset=["model"])
        )
        table = table.merge(train_time, on="model", how="left")
    else:
        table["train_time_sec"] = float("nan")

    if include_display_name:
        table.insert(1, "model_display", table["model"].map(_model_display_name))

    table["is_best_auc"] = table["auc_roc"] == table["auc_roc"].max()

    if model_order is None:
        model_order = DEFAULT_MODEL_ORDER
    order_lookup = {name: i for i, name in enumerate(model_order)}
    table["_order"] = table["model"].map(order_lookup).fillna(len(order_lookup)).astype(int)
    table = table.sort_values(["_order", "auc_roc"], ascending=[True, False]).drop(columns="_order")

    return table.reset_index(drop=True)

def format_model_comparison_table(
    comparison_table: pd.DataFrame,
) -> pd.DataFrame:
    """
    Make a display-friendly copy of ``build_model_comparison_table`` output.

    This is intended for notebook display or CSV reports. Keep the raw numeric
    table when you need sorting/filtering.
    """

    formatted = comparison_table.copy()

    if "model_display" in formatted.columns:
        formatted = formatted.rename(columns={"model_display": "Model"})
    elif "model" in formatted.columns:
        formatted = formatted.rename(columns={"model": "Model"})

    rename_map = {
        "auc_roc": "AUC-ROC",
        "auc_pr": "AUC-PR",
        "f1": "F1",
        "accuracy": "Accuracy",
        "train_time_sec": "Train Time",
        "auc_gap_train_minus_test": "AUC Gap",
        "is_best_auc": "Best AUC",
    }
    formatted = formatted.rename(columns=rename_map)

    for col in ["AUC-ROC", "AUC-PR", "F1"]:
        if col in formatted.columns:
            formatted[col] = formatted[col].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")

    if "Accuracy" in formatted.columns:
        formatted["Accuracy"] = formatted["Accuracy"].map(lambda x: "" if pd.isna(x) else f"{x * 100:.1f}%")

    if "Train Time" in formatted.columns:
        formatted["Train Time"] = formatted["Train Time"].map(lambda x: "" if pd.isna(x) else f"{x:.0f}s")

    if "AUC Gap" in formatted.columns:
        formatted["AUC Gap"] = formatted["AUC Gap"].map(lambda x: "" if pd.isna(x) else f"{x:+.3f}")

    keep_cols = [
        col for col in ["Model", "AUC-ROC", "AUC-PR", "F1", "Accuracy", "Train Time", "AUC Gap", "Best AUC"]
        if col in formatted.columns
    ]
    return formatted[keep_cols]

def build_roc_curve_table(
    pred_df: DataFrame,
    label_col: str = LABEL_COL,
    probability_col: str = PROBABILITY_COL,
    score_col: Optional[str] = None,
    positive_label: float = 1.0,
    num_bins: int = 1000,
) -> pd.DataFrame:
    """
    Build an ROC curve table from Spark model predictions.

    This avoids BinaryClassificationMetrics(...).roc(), which is not available
    in some PySpark Python wrappers.

    Returns
    -------
    pd.DataFrame
        Columns:
        - fpr: false positive rate
        - tpr: true positive rate
        - threshold_bin: approximate threshold bin
    """

    from pyspark.ml.functions import vector_to_array
    import pandas as pd

    # ------------------------------------------------------------------
    # Choose score column
    # ------------------------------------------------------------------
    # For XGBoost, Logistic Regression, Random Forest, and Decision Tree,
    # probability is usually a vector: [P(class 0), P(class 1)].
    # We use P(class 1) as the churn probability score.
    if score_col is not None:
        score_expr = F.col(score_col).cast("double")
    elif probability_col in pred_df.columns:
        score_expr = vector_to_array(F.col(probability_col))[1].cast("double")
    else:
        raise ValueError(
            f"Could not find score_col={score_col} or probability_col={probability_col} "
            "in pred_df. For SVM, you may need a separate rawPrediction-based helper."
        )

    # ------------------------------------------------------------------
    # Prepare label + score table
    # ------------------------------------------------------------------
    # Convert label into 1.0 for positive class and 0.0 otherwise.
    score_df = (
        pred_df
        .select(
            (F.col(label_col).cast("double") == F.lit(float(positive_label))).cast("double").alias("label"),
            score_expr.alias("score"),
        )
        .where(
            F.col("label").isNotNull()
            & F.col("score").isNotNull()
        )
    )

    # ------------------------------------------------------------------
    # Bin scores in Spark
    # ------------------------------------------------------------------
    # Exact ROC can create too many thresholds on a big validation set.
    # Binning gives a stable dashboard-style ROC curve without collecting
    # every prediction row to the driver.
    binned_df = (
        score_df
        .withColumn(
            "_score_bin",
            F.least(
                F.greatest(
                    F.floor(F.col("score") * F.lit(num_bins)).cast("int"),
                    F.lit(0),
                ),
                F.lit(num_bins - 1),
            )
        )
        .groupBy("_score_bin")
        .agg(
            F.sum("label").alias("pos"),
            (F.count("*") - F.sum("label")).alias("neg"),
        )
        .orderBy(F.desc("_score_bin"))
    )

    # ------------------------------------------------------------------
    # Collect only aggregated bins to Pandas
    # ------------------------------------------------------------------
    # This collects at most num_bins rows, not the full prediction dataset.
    pdf = binned_df.toPandas()

    if pdf.empty:
        return pd.DataFrame({
            "fpr": [0.0, 1.0],
            "tpr": [0.0, 1.0],
            "threshold_bin": [num_bins, 0],
        })

    # ------------------------------------------------------------------
    # Compute cumulative TPR/FPR
    # ------------------------------------------------------------------
    # Moving from high score to low score simulates lowering the threshold.
    total_pos = float(pdf["pos"].sum())
    total_neg = float(pdf["neg"].sum())

    if total_pos == 0 or total_neg == 0:
        raise ValueError(
            "ROC curve requires both positive and negative labels in pred_df."
        )

    pdf["cum_pos"] = pdf["pos"].cumsum()
    pdf["cum_neg"] = pdf["neg"].cumsum()

    pdf["tpr"] = pdf["cum_pos"] / total_pos
    pdf["fpr"] = pdf["cum_neg"] / total_neg
    pdf["threshold_bin"] = pdf["_score_bin"]

    # ------------------------------------------------------------------
    # Add ROC endpoints
    # ------------------------------------------------------------------
    # ROC curves conventionally include (0, 0) and (1, 1).
    roc_pdf = pd.concat(
        [
            pd.DataFrame({
                "fpr": [0.0],
                "tpr": [0.0],
                "threshold_bin": [num_bins],
            }),
            pdf[["fpr", "tpr", "threshold_bin"]],
            pd.DataFrame({
                "fpr": [1.0],
                "tpr": [1.0],
                "threshold_bin": [-1],
            }),
        ],
        ignore_index=True,
    )

    return roc_pdf

def build_confusion_matrix_table(       
    pred_df: DataFrame,
    label_col: str = LABEL_COL,
    prediction_col: str = PREDICTION_COL,
    negative_label: int = 0,
    positive_label: int = 1,
    negative_name: str = "Retained",
    positive_name: str = "Churned",
) -> pd.DataFrame:
    """
    Build a 2x2 confusion matrix table for the dashboard panel.

    For your churn setup, the default interpretation is:
    - 0 = retained
    - 1 = churned
    """

    counts = (
        pred_df
        .select(
            F.col(label_col).cast("int").alias("actual"),
            F.col(prediction_col).cast("int").alias("predicted"),
        )
        .groupBy("actual", "predicted")
        .count()
        .toPandas()
    )

    def lookup(actual: int, predicted: int) -> int:
        match = counts[(counts["actual"] == actual) & (counts["predicted"] == predicted)]
        if match.empty:
            return 0
        return int(match["count"].iloc[0])

    matrix = pd.DataFrame(
        [
            [lookup(negative_label, negative_label), lookup(negative_label, positive_label)],
            [lookup(positive_label, negative_label), lookup(positive_label, positive_label)],
        ],
        index=[negative_name, positive_name],
        columns=[negative_name, positive_name],
    )
    matrix.index.name = "Actual"
    matrix.columns.name = "Predicted"
    return matrix

def build_feature_importance_table(
    fitted_model: Any,
    feature_names: Optional[list[str]] = None,
    top_n: Optional[int] = 20,
    normalize: bool = True,
) -> pd.DataFrame:
    """
    Extract model feature importance for tree-based models.

    Supported cases:
    - Spark DecisionTree / RandomForest models via ``featureImportances``
    - XGBoost Spark models via ``get_feature_importances`` when available

    Linear models need a separate coefficient-based helper, so this function
    returns an empty table when native feature importance is unavailable.
    """

    importance_items: list[tuple[str, float]] = []

    if hasattr(fitted_model, "featureImportances"):
        values = list(fitted_model.featureImportances.toArray())
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(len(values))]
        importance_items = list(zip(feature_names, values))

    elif hasattr(fitted_model, "get_feature_importances"):
        raw_importance = fitted_model.get_feature_importances()
        if isinstance(raw_importance, dict):
            for key, value in raw_importance.items():
                feature_name = str(key)
                if feature_names is not None and feature_name.startswith("f") and feature_name[1:].isdigit():
                    idx = int(feature_name[1:])
                    if idx < len(feature_names):
                        feature_name = feature_names[idx]
                importance_items.append((feature_name, float(value)))

    importance_df = pd.DataFrame(importance_items, columns=["feature", "importance"])
    if importance_df.empty:
        return importance_df

    importance_df = importance_df.sort_values("importance", ascending=False).reset_index(drop=True)

    if normalize:
        total = importance_df["importance"].sum()
        if total > 0:
            importance_df["importance"] = importance_df["importance"] / total

    if top_n is not None:
        importance_df = importance_df.head(top_n).reset_index(drop=True)

    return importance_df


# ----------------------------------
# Model Metric Visualization
# ----------------------------------
def plot_model_comparison(
    metrics_df,
    metrics_to_plot: Optional[list[str]] = None,
    split: str = "test",
    score_scale: float = 100.0,
    ylim: tuple[float, float] = (0, 105),
    sort_desc: bool = True,
) -> dict[str, Any]:
    """
    Plot one model-comparison bar chart per metric.

    This function takes the long-form metrics table produced by
    train_evaluate_models(...)[\"metrics_df\"] and creates one bar chart
    for each selected metric.

    Example:
        One chart for accuracy.
        One chart for F1.
        One chart for AUC.
        etc.
    """

    # ------------------------------------------------------------------
    # Default metric selection
    # ------------------------------------------------------------------
    if metrics_to_plot is None:
        metrics_to_plot = MODEL_COMPARISON_METRICS

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------
    # The plotting logic requires:
    # - model: model name, e.g. log_reg, random_forest
    # - metric: metric name, e.g. accuracy, f1, auc
    # - split: score column to plot, usually test or train
    required_cols = {"model", "metric", split}
    missing = required_cols - set(metrics_df.columns)
    if missing:
        raise ValueError(f"metrics_df is missing required columns: {sorted(missing)}")

    # ------------------------------------------------------------------
    # Filter metrics and scale scores
    # ------------------------------------------------------------------
    # Keep only the selected metrics.
    # Then create a display column that converts scores like 0.842 into 84.2.

    plot_df = metrics_df[metrics_df["metric"].isin(metrics_to_plot)].copy()
    plot_df[f"{split}_percent"] = plot_df[split] * score_scale

    # ------------------------------------------------------------------
    # Generate one chart per metric
    # ------------------------------------------------------------------
    # Store each matplotlib Figure so the caller can further customize
    figures: dict[str, Any] = {}

    # Loop through each requested metric and create a separate bar chart.
    for metric in metrics_to_plot:
        # Select rows for one metric only.
        temp = plot_df[plot_df["metric"] == metric].copy()

        # Skip metrics that are requested but not present in metrics_df.
        if temp.empty:
            continue

        # Optionally sort models from best to worst for this metric.
        if sort_desc:
            temp = temp.sort_values(f"{split}_percent", ascending=False)

        # --------------------------------------------------------------
        # Create the bar chart
        # --------------------------------------------------------------
        # Each bar represents one model's score for the current metric.
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(temp["model"], temp[f"{split}_percent"])

        # --------------------------------------------------------------
        # Axis labels and annotations
        # --------------------------------------------------------------
        # The y-axis label changes depending on whether the plotted split
        # is test, train, validation, etc.
        ax.set_ylabel(f"{split.title()} Score (%)")
        ax.set_xlabel("Model")
        ax.set_title(f"Model Comparison: {metric}")
        ax.set_ylim(*ylim)

        # Add percentage labels above each bar, such as 84.3%.
        for i, v in enumerate(temp[f"{split}_percent"]):
            ax.text(i, v + 1, f"{v:.1f}%", ha="center")

        # --------------------------------------------------------------
        # Return figure object
        # --------------------------------------------------------------
        # Prevent labels/title from being cut off.
        fig.tight_layout()
        plt.show()

        # Keep the figure object in the return dictionary.
        figures[metric] = fig
    return figures

def plot_model_train_test_comparison(
    metrics_df,
    metrics_to_plot: Optional[list[str]] = None,
    score_scale: float = 100.0,
    ylim: tuple[float, float] = (0, 105),
    validation_label: str = "Validation/Test",
) -> dict[str, Any]:
    """
    Plot train vs validation/test metric bars for each model.

    This function takes the long-form metrics table produced by
    train_evaluate_models(...)[\"metrics_df\"] and creates one grouped bar chart
    per model.

    Each chart compares the model's train score against its validation/test score
    for selected metrics such as accuracy, F1, recall, precision, and AUC.
    """

    # ------------------------------------------------------------------
    # Default metric selection
    # ------------------------------------------------------------------
    # If the caller does not specify which metrics to compare, use the
    # default train-vs-test metrics from the source constant.
    if metrics_to_plot is None:
        metrics_to_plot = MODEL_TRAIN_TEST_COMPARISON_METRICS

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------
    # The plotting logic requires:
    # - model: model name, e.g. log_reg, random_forest
    # - metric: metric name, e.g. accuracy, f1, auc
    # - train: training score
    # - test: validation/test score
    required_cols = {"model", "metric", "train", "test"}
    missing = required_cols - set(metrics_df.columns)
    if missing:
        raise ValueError(f"metrics_df is missing required columns: {sorted(missing)}")

    # ------------------------------------------------------------------
    # Filter metrics and scale scores
    # ------------------------------------------------------------------
    # Keep only the selected metrics.
    # Then convert raw metric scores like 0.842 into display values like 84.2.
    plot_df = metrics_df[metrics_df["metric"].isin(metrics_to_plot)].copy()
    plot_df["train_percent"] = plot_df["train"] * score_scale
    plot_df["test_percent"] = plot_df["test"] * score_scale

    # ------------------------------------------------------------------
    # Generate one chart per model
    # ------------------------------------------------------------------
    # Store each matplotlib Figure so the caller can further customize,
    figures: dict[str, Any] = {}

    # For each model, plot all selected metrics side by side.
    # Each metric gets two bars:
    # - train score
    # - validation/test score
    for model_name in plot_df["model"].unique():
        # Select rows for one model only.
        temp = plot_df[plot_df["model"] == model_name].copy()

        # Ensure metric labels are strings so matplotlib can display them cleanly.
        temp["metric"] = temp["metric"].astype(str)

        # --------------------------------------------------------------
        # Bar-position setup
        # --------------------------------------------------------------
        # x controls the center location for each metric group.
        # width controls how wide each train/test bar should be.
        x = list(range(len(temp)))
        width = 0.35

        # --------------------------------------------------------------
        # Create grouped bar chart
        # --------------------------------------------------------------
        # The train bars are shifted slightly left.
        # The validation/test bars are shifted slightly right.
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(
            [i - width / 2 for i in x],
            temp["train_percent"],
            width=width,
            label="Train",
        )
        ax.bar(
            [i + width / 2 for i in x],
            temp["test_percent"],
            width=width,
            label=validation_label,
        )

        # --------------------------------------------------------------
        # Axis labels and chart title
        # --------------------------------------------------------------
        # Use metric names as x-axis labels.
        # Rotate labels slightly to reduce overlap.
        ax.set_xticks(x)
        ax.set_xticklabels(temp["metric"], rotation=20)
        ax.set_ylabel("Score (%)")
        ax.set_title(f"Train vs Validation/Test Metrics: {model_name}")
        ax.set_ylim(*ylim)
        ax.legend()

        # --------------------------------------------------------------
        # Return figure object
        # --------------------------------------------------------------
        # Prevent axis labels, title, or legend from being cut off.
        fig.tight_layout()
        plt.show()

        # Keep the figure object in the return dictionary using model name
        # as the key.
        figures[model_name] = fig
    return figures

def plot_validation_auc_by_model(
    metrics_df: pd.DataFrame,
    split: str = "test",
    ylim: tuple[float, float] = (0.70, 0.92),
    model_order: Optional[list[str]] = None,
    dark: bool = True,
) -> Any:
    """
    Plot the dashboard-style "AUC-ROC by model" bar chart.

    This chart compares validation/test AUC-ROC across models.
    It matches the dashboard card in your PNG where each bar represents
    one model's validation/test AUC-ROC score.
    """

    # ------------------------------------------------------------------
    # Build comparison table
    # ------------------------------------------------------------------
    # Convert the long-form metrics_df into a model-level comparison table.
    # This table should contain one row per model and columns such as:
    # - model
    # - model_display
    # - auc_roc
    # - auc_pr
    # - f1
    # - accuracy
    table = build_model_comparison_table(
        metrics_df,
        model_order=model_order,
        split=split,
    )

    # ------------------------------------------------------------------
    # Sort models by validation/test AUC-ROC
    # ------------------------------------------------------------------
    # Sort from highest AUC-ROC to lowest so the strongest model appears first.
    table = table.sort_values("auc_roc", ascending=False)

    # ------------------------------------------------------------------
    # Create figure and axes
    # ------------------------------------------------------------------
    # Create one dashboard-style bar chart.
    fig, ax = plt.subplots(figsize=(9, 4.8))

    # Apply dark dashboard styling when requested.
    if dark:
        _apply_dark_axes_style(ax)

    # ------------------------------------------------------------------
    # Prepare labels and bars
    # ------------------------------------------------------------------
    # Prefer readable display names when available.
    # Fall back to raw model names if model_display does not exist.
    labels = table.get("model_display", table["model"])

    # Draw one bar per model using validation/test AUC-ROC.
    bars = ax.bar(labels, table["auc_roc"])

    # ------------------------------------------------------------------
    # Bar annotations
    # ------------------------------------------------------------------
    # Add exact AUC-ROC values above each bar, such as 0.877.
    for bar, value in zip(bars, table["auc_roc"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.005,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            color="#c7d3e3" if dark else "black",
            fontsize=9,
        )

    # ------------------------------------------------------------------
    # Axis labels and title
    # ------------------------------------------------------------------
    ax.set_title("AUC-ROC by model")
    ax.set_ylabel("AUC-ROC")
    ax.set_xlabel("Model")
    ax.set_ylim(*ylim)

    # ------------------------------------------------------------------
    # Layout cleanup
    # ------------------------------------------------------------------
    # Prevent title, labels, or annotations from being cut off.
    fig.tight_layout()
    plt.show()
    return fig

def plot_train_validation_auc(
    metrics_df: pd.DataFrame,
    ylim: tuple[float, float] = (0.70, 0.92),
    validation_label: str = "Validation",
    model_order: Optional[list[str]] = None,
    dark: bool = True,
) -> Any:
    """
    Plot the dashboard-style train vs validation AUC grouped bar chart.

    This chart compares train AUC-ROC against validation/test AUC-ROC
    for each model. It is useful for quickly checking generalization gap.
    """

    # ------------------------------------------------------------------
    # Filter to AUC-ROC rows only
    # ------------------------------------------------------------------
    # The long-form metrics_df contains many metrics.
    # This plot only needs areaUnderROC.
    auc_df = metrics_df[metrics_df["metric"] == "areaUnderROC"].copy()

    # Raise a clear error if the required metric is missing.
    if auc_df.empty:
        raise ValueError("metrics_df does not contain metric='areaUnderROC'.")

    # ------------------------------------------------------------------
    # Determine model order
    # ------------------------------------------------------------------
    # Use the provided model_order when available.
    # Otherwise, fall back to the project default model order.
    if model_order is None:
        model_order = DEFAULT_MODEL_ORDER

    # Create lookup table so models appear in a consistent dashboard order.
    order_lookup = {
        name: i
        for i, name in enumerate(model_order)
    }

    # Assign numeric ordering to each model.
    # Unknown models are placed after the known default models.
    auc_df["_order"] = (
        auc_df["model"]
        .map(order_lookup)
        .fillna(len(order_lookup))
        .astype(int)
    )

    # Sort rows by model order.
    auc_df = auc_df.sort_values("_order")

    # Convert internal model names into readable display names.
    auc_df["model_display"] = auc_df["model"].map(_model_display_name)

    # ------------------------------------------------------------------
    # Bar-position setup
    # ------------------------------------------------------------------
    # x stores the center position for each model group.
    # width controls the width of each train/validation bar.
    x = list(range(len(auc_df)))
    width = 0.35

    # ------------------------------------------------------------------
    # Create figure and axes
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4.8))

    # Apply dark dashboard styling when requested.
    if dark:
        _apply_dark_axes_style(ax)

    # ------------------------------------------------------------------
    # Create grouped bars
    # ------------------------------------------------------------------
    # Train bars are shifted slightly left.
    ax.bar(
        [i - width / 2 for i in x],
        auc_df["train"],
        width=width,
        label="Train",
    )

    # Validation/test bars are shifted slightly right.
    ax.bar(
        [i + width / 2 for i in x],
        auc_df["test"],
        width=width,
        label=validation_label,
    )

    # ------------------------------------------------------------------
    # Axis labels, title, and legend
    # ------------------------------------------------------------------
    ax.set_title("Train vs. validation AUC")
    ax.set_ylabel("AUC-ROC")
    ax.set_xlabel("Model")
    ax.set_ylim(*ylim)
    ax.set_xticks(x)
    ax.set_xticklabels(auc_df["model_display"], rotation=0)
    ax.legend(frameon=False)

    # ------------------------------------------------------------------
    # Layout cleanup
    # ------------------------------------------------------------------
    fig.tight_layout()
    plt.show()
    return fig

def plot_roc_curve(
    roc_df: pd.DataFrame,
    model_name: str,
    auc_roc: Optional[float] = None,
    dark: bool = True,
) -> Any:
    """
    Plot one ROC curve for the model-explorer panel.

    The ROC curve shows the tradeoff between false positive rate and
    true positive rate across classification thresholds.
    """

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------
    # ROC plotting requires:
    # - fpr: false positive rate
    # - tpr: true positive rate
    required_cols = {"fpr", "tpr"}
    missing = required_cols - set(roc_df.columns)

    if missing:
        raise ValueError(f"roc_df is missing required columns: {sorted(missing)}")

    # ------------------------------------------------------------------
    # Create figure and axes
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8.5, 4.8))

    # Apply dark dashboard styling when requested.
    if dark:
        _apply_dark_axes_style(ax)

    # ------------------------------------------------------------------
    # Plot ROC curve
    # ------------------------------------------------------------------
    # The main curve plots true positive rate against false positive rate.
    ax.plot(
        roc_df["fpr"],
        roc_df["tpr"],
        marker="o",
        markersize=2,
        linewidth=2,
    )

    # ------------------------------------------------------------------
    # Plot random-baseline diagonal
    # ------------------------------------------------------------------
    # The dashed diagonal represents random guessing.
    # A useful classifier should generally appear above this line.
    ax.plot(
        [0, 1],
        [0, 1],
        linestyle="--",
        linewidth=1.2,
        alpha=0.7,
    )

    # ------------------------------------------------------------------
    # Axis limits and labels
    # ------------------------------------------------------------------
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")

    # ------------------------------------------------------------------
    # Title construction
    # ------------------------------------------------------------------
    # Use readable model name.
    # Include AUC score in the title when provided.
    title = f"ROC curve: {_model_display_name(model_name)}"

    if auc_roc is not None:
        title += f" (AUC={auc_roc:.3f})"

    ax.set_title(title)

    # ------------------------------------------------------------------
    # Layout cleanup
    # ------------------------------------------------------------------
    fig.tight_layout()
    plt.show()
    return fig

def plot_confusion_matrix(
    cm_df: pd.DataFrame,
    model_name: str,
    dark: bool = True,
) -> Any:
    """
    Plot a dashboard-style confusion matrix from build_confusion_matrix_table.

    The confusion matrix shows how many examples fall into each actual/predicted
    class combination.
    """

    # ------------------------------------------------------------------
    # Create figure and axes
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.8, 4.8))

    # Apply dark dashboard styling when requested.
    if dark:
        _apply_dark_axes_style(ax)

    # ------------------------------------------------------------------
    # Draw matrix image
    # ------------------------------------------------------------------
    # imshow displays the confusion matrix values as a heatmap.
    image = ax.imshow(cm_df.values)

    # ------------------------------------------------------------------
    # Axis and annotation setup
    # ------------------------------------------------------------------
    # Columns are predicted labels.
    # Index values are actual labels.
    ax.set_xticks(range(cm_df.shape[1]))
    ax.set_yticks(range(cm_df.shape[0]))
    ax.set_xticklabels(cm_df.columns)
    ax.set_yticklabels(cm_df.index)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(f"Confusion matrix: {_model_display_name(model_name)}")

    # ------------------------------------------------------------------
    # Cell annotations
    # ------------------------------------------------------------------
    # Write the raw count inside each matrix cell.
    # Example:
    # - true positives
    # - false positives
    # - false negatives
    # - true negatives
    for i in range(cm_df.shape[0]):
        for j in range(cm_df.shape[1]):
            ax.text(
                j,
                i,
                f"{int(cm_df.iloc[i, j]):,}",
                ha="center",
                va="center",
                color="#f3f6fb" if dark else "black",
                fontsize=12,
                fontweight="bold",
            )

    # ------------------------------------------------------------------
    # Color scale
    # ------------------------------------------------------------------
    # Add a colorbar so the heatmap intensity has a visible scale.
    fig.colorbar(
        image,
        ax=ax,
        fraction=0.046,
        pad=0.04,
    )


    fig.tight_layout()
    plt.show()
    return fig

def plot_feature_importance(
    importance_df: pd.DataFrame,
    model_name: str,
    top_n: int = 15,
    dark: bool = True,
) -> Any:
    """
    Plot feature importance in the horizontal-bar style shown in the PNG.

    This chart shows which features contributed most strongly to a fitted
    tree-based model, such as Random Forest or XGBoost.
    """

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------
    # Feature importance plotting requires:
    # - feature: feature name
    # - importance: numeric importance score
    required_cols = {"feature", "importance"}
    missing = required_cols - set(importance_df.columns)

    if missing:
        raise ValueError(
            f"importance_df is missing required columns: {sorted(missing)}"
        )

    # ------------------------------------------------------------------
    # Select top features
    # ------------------------------------------------------------------
    # First sort from most important to least important.
    # Then keep only the top_n most important features.
    temp = (
        importance_df
        .sort_values("importance", ascending=False)
        .head(top_n)
        .copy()
    )

    # ------------------------------------------------------------------
    # Reverse order for horizontal plotting
    # ------------------------------------------------------------------
    # Sorting ascending here makes the most important feature appear at the top
    # after matplotlib draws the horizontal bars.
    temp = temp.sort_values("importance", ascending=True)

    # ------------------------------------------------------------------
    # Create figure and axes
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.2))

    # Apply dark dashboard styling when requested.
    if dark:
        _apply_dark_axes_style(ax)

    # ------------------------------------------------------------------
    # Create horizontal bar chart
    # ------------------------------------------------------------------
    # Each bar represents one feature's relative importance.
    ax.barh(
        temp["feature"],
        temp["importance"],
    )

    # ------------------------------------------------------------------
    # Axis and annotation setup
    # ------------------------------------------------------------------
    ax.set_xlabel("Relative importance")
    ax.set_ylabel("Feature")
    ax.set_title(f"Feature importance: {_model_display_name(model_name)}")
    # Add percentage labels at the end of each bar.
    for y, value in enumerate(temp["importance"]):
        ax.text(
            value,
            y,
            f" {value * 100:.1f}%",
            va="center",
            color="#c7d3e3" if dark else "black",
            fontsize=9,
        )

    # ------------------------------------------------------------------
    # Layout cleanup
    # ------------------------------------------------------------------
    fig.tight_layout()
    plt.show()
    return fig


# ----------------------------------
# Orchestration Builder
# ----------------------------------
def fit_transform_evaluate_models(
    model_names: list[str],
    train_final_df: DataFrame,
    test_final_df: DataFrame,
    spark: SparkSession,
    mode: str = "EXPANSE",
    metrics: Optional[list[str]] = None,
    cache: bool = True,
    keep_predictions: bool = False,
    cast_xgb_label_to_int: bool = True,
    label_col: str = LABEL_COL,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Train several models, evaluate them, and return metric tables.

    Returns
    -------
    dict
        {
            "metrics_df": long-form Pandas DataFrame,
            "presentation_metrics": wide Pandas DataFrame using test scores,
            "predictions": optional fitted models/predictions if keep_predictions=True,
            "metric_rows": raw list of metric row dictionaries,
        }
    """

    metric_rows: list[dict[str, Any]] = []
    predictions: dict[str, dict[str, Any]] = {}

    for model_name in model_names:
        if verbose:
            print(f"\n===== Training {model_name} =====")

        train_for_model = train_final_df
        test_for_model = test_final_df

        if cast_xgb_label_to_int and model_name == "xgb":
            train_for_model = _prepare_model_frame_for_xgb(train_for_model, label_col=label_col)
            test_for_model = _prepare_model_frame_for_xgb(test_for_model, label_col=label_col)

        start_time = time.perf_counter()
        fitted_model, train_pred_df, test_pred_df = fit_transform_model(
            model_name=model_name,
            train_final_df=train_for_model,
            test_final_df=test_for_model,
            spark=spark,
            cache=cache,
            mode=mode,
        )
        train_time_sec = time.perf_counter() - start_time

        metric_dict = evaluate_model(
            model_name=model_name,
            train_pred_df=train_pred_df,
            test_pred_df=test_pred_df,
            label_col=label_col,
            metrics=metrics,
            verbose=verbose,
            unpersist=False,
        )

        metric_rows.extend(metric_dict_to_rows(model_name, metric_dict, train_time_sec=train_time_sec))

        if keep_predictions:
            predictions[model_name] = {
                "model": fitted_model,
                "train_pred": train_pred_df,
                "test_pred": test_pred_df,
            }
        else:
            train_pred_df.unpersist()
            test_pred_df.unpersist()

    metrics_df = rows_to_pandas_df(metric_rows)
    presentation_metrics = build_presentation_metrics(metrics_df, split="test")

    return {
        "metrics_df": metrics_df,
        "presentation_metrics": presentation_metrics,
        "predictions": predictions,
        "metric_rows": metric_rows,
    }

def build_model_report_assets(
    results: dict[str, Any],
    feature_names: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Build the core assets needed by the attached dashboard mockups.

    Expected input is the dictionary returned by ``fit_transform_evaluate_models``.
    Use ``keep_predictions=True`` when calling that function if you also want
    ROC curves and confusion matrices.
    """

    metrics_df = results["metrics_df"]
    predictions = results.get("predictions", {})

    assets: dict[str, Any] = {}
    assets["comparison_table_raw"] = build_model_comparison_table(metrics_df)
    assets["comparison_table_display"] = format_model_comparison_table(assets["comparison_table_raw"])
    assets["fig_auc_by_model"] = plot_validation_auc_by_model(metrics_df)
    assets["fig_train_validation_auc"] = plot_train_validation_auc(metrics_df)

    model_assets: dict[str, Any] = {}
    for model_name, bundle in predictions.items():
        fitted_model = bundle.get("model")
        test_pred_df = bundle.get("test_pred")

        per_model: dict[str, Any] = {}

        if fitted_model is not None:
            importance_df = build_feature_importance_table(fitted_model, feature_names=feature_names, top_n=20)
            per_model["feature_importance"] = importance_df
            if not importance_df.empty:
                per_model["fig_feature_importance"] = plot_feature_importance(
                    importance_df,
                    model_name=model_name,
                )

        if test_pred_df is not None:
            roc_df = build_roc_curve_table(test_pred_df)
            per_model["roc_curve"] = roc_df

            auc_row = metrics_df[(metrics_df["model"] == model_name) & (metrics_df["metric"] == "areaUnderROC")]
            auc_roc = None if auc_row.empty else float(auc_row["test"].iloc[0])
            per_model["fig_roc_curve"] = plot_roc_curve(
                roc_df,
                model_name=model_name,
                auc_roc=auc_roc,
            )

            cm_df = build_confusion_matrix_table(test_pred_df)
            per_model["confusion_matrix"] = cm_df
            per_model["fig_confusion_matrix"] = plot_confusion_matrix(
                cm_df,
                model_name=model_name,
            )

        model_assets[model_name] = per_model

    assets["model_assets"] = model_assets

    return assets


# ----------------------------------
# Hyperparameter Tuning (Cross-Validation)
# ----------------------------------
def build_param_grid(
    model: SparkClassifier,
    param_spec: dict[str, list[Any]],
) -> list:
    """
    Build a Spark ``ParamGridBuilder`` grid from a ``{param_name: [values]}`` spec.

    ``param_name`` keys must match params on ``model`` (the same names used in
    build_models, e.g. ``regParam`` for LogisticRegression or ``max_depth`` for
    the XGBoost estimator). An empty spec yields a single-point grid that runs
    cross-validation on the baseline params from build_models().
    """

    builder = ParamGridBuilder()
    for param_name, values in param_spec.items():
        try:
            param = model.getParam(param_name)
        except Exception as exc:  # ValueError / AttributeError depending on estimator
            raise ValueError(
                f"{type(model).__name__} has no tunable param '{param_name}'."
            ) from exc
        builder = builder.addGrid(param, list(values))
    return builder.build()

def cross_validate_model(
    model_name: str,
    train_final_df: DataFrame,
    spark: SparkSession,
    param_grid: Optional[dict[str, list[Any]]] = None,
    num_folds: int = 5,
    metric: str = "areaUnderROC",
    parallelism: int = 2,
    mode: str = "EXPANSE",
    seed: int = SEED,
    cast_xgb_label_to_int: bool = True,
    label_col: str = LABEL_COL,
    prediction_col: str = PREDICTION_COL,
    raw_prediction_col: str = RAW_PREDICTION_COL,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Run k-fold cross-validation for one model and return the tuning results.

    The estimator and its baseline params come from ``build_models`` so tuning
    stays consistent with the rest of the modeling pipeline. ``param_grid``
    defaults to ``DEFAULT_PARAM_GRIDS[model_name]`` when not supplied; pass
    ``{}`` to cross-validate the baseline params with no search.

    Returns
    -------
    dict
        {
            "model_name": str,
            "cv_model": CrossValidatorModel,
            "best_model": cv_model.bestModel (refit on full train data),
            "evaluator": the tuning evaluator,
            "metric": metric name used for selection,
            "param_maps": estimatorParamMaps,
            "avg_metrics": per-combo cross-validation scores,
            "best_params": {param_name: value} of the winning combo,
            "best_avg_metric": cross-validation score of the winning combo,
            "results_df": Pandas table of params + cv score, sorted best-first,
        }
    """

    models = build_models(spark, mode=mode)
    if model_name not in models:
        raise ValueError(
            f"Model name not found: {model_name}. "
            f"Available models: {sorted(models)}"
        )
    estimator = models[model_name]

    if param_grid is None:
        param_grid = DEFAULT_PARAM_GRIDS.get(model_name, {})
    grid = build_param_grid(estimator, param_grid)

    evaluator = _build_evaluator(
        metric=metric,
        label_col=label_col,
        prediction_col=prediction_col,
        raw_prediction_col=raw_prediction_col,
    )

    # XGBoost Spark expects an integer class label, matching the baseline pipeline.
    train_for_cv = train_final_df
    if cast_xgb_label_to_int and model_name == "xgb":
        train_for_cv = _prepare_model_frame_for_xgb(train_for_cv, label_col=label_col)

    cv = CrossValidator(
        estimator=estimator,
        estimatorParamMaps=grid,
        evaluator=evaluator,
        numFolds=num_folds,
        seed=seed,
        parallelism=parallelism,
    )

    if verbose:
        print(
            f"\n===== Cross-validating {model_name} "
            f"({len(grid)} param combo(s) x {num_folds} folds) ====="
        )

    cv_model = cv.fit(train_for_cv)

    avg_metrics = [float(m) for m in cv_model.avgMetrics]
    results_df = _cv_results_to_df(grid, avg_metrics, metric)

    # CrossValidator already refits bestModel; recover which combo it picked so we
    # can report the winning params. isLargerBetter() handles metric direction.
    if avg_metrics:
        if evaluator.isLargerBetter():
            best_index = max(range(len(avg_metrics)), key=lambda i: avg_metrics[i])
        else:
            best_index = min(range(len(avg_metrics)), key=lambda i: avg_metrics[i])
        best_avg_metric = avg_metrics[best_index]
    else:
        best_index = 0
        best_avg_metric = float("nan")

    best_params = _param_map_to_dict(grid[best_index]) if grid else {}

    if verbose:
        print(f"{model_name} best CV {metric}: {best_avg_metric:.4f}")
        if best_params:
            print(f"{model_name} best params: {best_params}")

    return {
        "model_name": model_name,
        "cv_model": cv_model,
        "best_model": cv_model.bestModel,
        "evaluator": evaluator,
        "metric": metric,
        "param_maps": grid,
        "avg_metrics": avg_metrics,
        "best_params": best_params,
        "best_avg_metric": best_avg_metric,
        "results_df": results_df,
    }


# ----------------------------------
# Model Persistence (Save / Load)
# ----------------------------------
def save_model(
    fitted_model: Any,
    model_name: str,
    models_dir: str | Path,
    overwrite: bool = True,
) -> str:
    """
    Save a fitted model to ``<models_dir>/<model_name>`` and return that path.

    Works for any Spark ML model produced by this pipeline (Logistic Regression,
    Decision Tree, Random Forest, LinearSVC) as well as the XGBoost Spark model,
    since all expose the standard MLWritable ``write()`` API. The tuned
    ``best_model`` from ``cross_validate_model`` is also a fitted model and can be
    saved directly.

    Reload with :func:`load_model` using the same ``model_name`` so the correct
    Spark loader class is selected.
    """

    _require_active_spark(f"save model '{model_name}'")

    path = str(Path(models_dir) / model_name)

    writer = fitted_model.write()
    if overwrite:
        writer = writer.overwrite()
    writer.save(path)

    print(f"Saved {model_name} model to: {path}")
    return path

def load_model(
    model_name: str,
    models_dir: str | Path,
) -> Any:
    """
    Load a fitted model saved by :func:`save_model` from
    ``<models_dir>/<model_name>``.

    ``model_name`` selects the loader class via ``MODEL_LOADER_CLASSES``, so it
    must match the name used when saving (e.g. ``"xgb"``, ``"log_reg"``).
    """

    if model_name not in MODEL_LOADER_CLASSES:
        raise ValueError(
            f"No loader registered for model '{model_name}'. "
            f"Known models: {sorted(MODEL_LOADER_CLASSES)}"
        )

    _require_active_spark(f"load model '{model_name}'")

    path = str(Path(models_dir) / model_name)
    model = MODEL_LOADER_CLASSES[model_name].load(path)

    print(f"Loaded {model_name} model from: {path}")
    return model


# ----------------------------------
# Helper Functions
# ----------------------------------
def _require_active_spark(action: str) -> None:
    """
    Raise a clear error if there is no active SparkSession.

    Fitted Spark models are handles into the JVM, so saving/loading them needs a
    live session. Without this guard, PySpark fails deep inside its internals
    with a bare ``AssertionError`` (``assert sc is not None ...``). This turns
    that into an actionable message.
    """

    if SparkSession.getActiveSession() is None:
        raise RuntimeError(
            f"Cannot {action}: no active SparkSession. Re-run the cell that "
            "creates the session (create_spark_session(...)) and the training "
            "cells before saving/loading, and call spark.stop() only as the very "
            "last step. A fitted model cannot be written or read once its Spark "
            "session has stopped."
        )

def _build_evaluator(
    metric: str,
    label_col: str = LABEL_COL,
    prediction_col: str = PREDICTION_COL,
    raw_prediction_col: str = RAW_PREDICTION_COL,
):
    """
    Build the right Spark evaluator for a metric name.

    Binary metrics use BinaryClassificationEvaluator (rawPrediction); multiclass
    metrics use MulticlassClassificationEvaluator (prediction). Centralizing this
    keeps evaluate_model, evaluate_split, and cross_validate_model in sync.
    """

    if metric in BINARY_METRICS:
        return BinaryClassificationEvaluator(
            labelCol=label_col,
            rawPredictionCol=raw_prediction_col,
            metricName=metric,
        )
    if metric in MULTICLASS_METRICS:
        return MulticlassClassificationEvaluator(
            labelCol=label_col,
            predictionCol=prediction_col,
            metricName=metric,
        )
    raise ValueError(
        f"Unsupported metric: {metric}. "
        f"Supported metrics are: {sorted(BINARY_METRICS | MULTICLASS_METRICS)}"
    )

def _param_map_to_dict(param_map: Any) -> dict[str, Any]:
    """
    Convert a Spark ParamMap ({Param: value}) into a readable {name: value} dict.
    """

    return {param.name: value for param, value in param_map.items()}

def _cv_results_to_df(
    param_maps: list,
    avg_metrics: list[float],
    metric: str,
) -> pd.DataFrame:
    """
    Build a tidy Pandas table of cross-validation results, sorted best-first.

    One row per param combo, with the tuned params as columns plus a
    ``cv_<metric>`` score column.
    """

    score_col = f"cv_{metric}"
    rows = []
    for pm, score in zip(param_maps, avg_metrics):
        row = _param_map_to_dict(pm)
        row[score_col] = score
        rows.append(row)

    results_df = pd.DataFrame(rows)
    if not results_df.empty and score_col in results_df.columns:
        results_df = results_df.sort_values(score_col, ascending=False).reset_index(drop=True)
    return results_df

def _prepare_model_frame_for_xgb(
    df: DataFrame,
    label_col: str = LABEL_COL,
) -> DataFrame:
    """
    XGBoost Spark expects a numeric class label. This keeps that fix centralized.
    """

    return df.withColumn(label_col, F.col(label_col).cast("int"))

def _model_display_name(model_name: str) -> str:
    """
    Convert internal model keys such as ``random_forest`` into display names
    such as ``Random Forest``.
    """

    return MODEL_DISPLAY_NAMES.get(model_name, model_name)

def _metric_value(
    wide_df: pd.DataFrame,
    metric_name: str,
    default: float = float("nan"),
) -> pd.Series:
    """
    Safely pull one metric column from a wide metric table.

    This prevents table generation from failing when a metric was not computed.
    """

    if metric_name in wide_df.columns:
        return wide_df[metric_name]
    return pd.Series([default] * len(wide_df), index=wide_df.index)

def _apply_dark_axes_style(ax: Any) -> None:
    """
    Apply a lightweight dark style similar to the attached dashboard mockups.

    This is intentionally contained in one helper so you can turn the style off
    or replace it later without rewriting the metric logic.
    """

    fig = ax.figure
    fig.patch.set_facecolor("#08111f")
    ax.set_facecolor("#0f1b2d")
    ax.tick_params(colors="#c7d3e3")
    ax.xaxis.label.set_color("#c7d3e3")
    ax.yaxis.label.set_color("#c7d3e3")
    ax.title.set_color("#f3f6fb")
    for spine in ax.spines.values():
        spine.set_color("#23344e")
    ax.grid(axis="y", alpha=0.22, color="#d8e6ff")
    ax.set_axisbelow(True)