# -----------------------------
# Import Modules
# -----------------------------
# Spark
from pyspark import StorageLevel
from pyspark.sql import SparkSession, DataFrame

# ML
from pyspark.ml.classification import (
    LogisticRegression, 
    DecisionTreeClassifier,
    RandomForestClassifier,
    LinearSVC
)
from xgboost.spark import SparkXGBClassifier
from pyspark.ml.evaluation import (
    BinaryClassificationEvaluator,
    MulticlassClassificationEvaluator
)

# Others
from typing import TypeAlias, Optional, Any

# -----------------------------
# ML Constants
# -----------------------------
FEATURE_COL = "finalized_features"
LABEL_COL = "churn"
PREDICTION_COL = "prediction"
RAW_PREDICTION_COL = "rawPrediction"
PROBABILITY_COL = "probability"

SEED = 42

SparkClassifier: TypeAlias = (
    LogisticRegression
    | DecisionTreeClassifier
    | RandomForestClassifier
    | LinearSVC
    | SparkXGBClassifier
)


# -----------------------------
# XG Boost Config
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
# Model Definition
# ----------------------------------
def build_models(
    spark: SparkSession,
    mode: str = "EXPANSE"
) -> dict[str, SparkClassifier]:
    total_cores = 1
    if mode.upper() == "EXPANSE":
        total_cores = get_spark_resources(spark)['total_cores']
        print(f"total_cores has {total_cores}")
    elif mode.upper() == "COLAB":
        total_cores = 1
    elif mode.upper() == "LOCAL":
        total_cores = 7
    else:
        raise Exception("Invalid mode, the only acceptible are 'EXPANSE', 'COLAB', 'LOCAL'")

    return {
        "log_reg": LogisticRegression(
            featuresCol=FEATURE_COL,
            labelCol=LABEL_COL,
            predictionCol=PREDICTION_COL,
            rawPredictionCol=RAW_PREDICTION_COL,
            probabilityCol=PROBABILITY_COL,
    
            # baseline params
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
    
            # baseline params
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
    
            # baseline params
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
    
            # baseline params
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
    
            # baseline params
            num_workers=total_cores,
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            seed=SEED,
        ),
    }


# ----------------------------------
# Model Fit & Transform
# ----------------------------------
def fit_transform_model(
    model_name: str,
    train_final_df: DataFrame,
    test_final_df: DataFrame,
    spark: SparkSession,
    cache: bool = False,
    mode: str = "EXPANSE"
) -> tuple[Any, DataFrame, DataFrame]:

    MODELS = build_models(spark, mode=mode)
    if model_name not in MODELS:
        raise ValueError("Model Name NOT FOUND!!!")        
    
    # Define model  
    model = MODELS[model_name]

    # Fit and transform
    fitted = model.fit(train_final_df)
    train_pred_df = fitted.transform(train_final_df)
    test_pred_df = fitted.transform(test_final_df)

    # Cache if requested
    if cache:
        train_pred_df = train_pred_df.persist(StorageLevel.MEMORY_AND_DISK)
        test_pred_df = test_pred_df.persist(StorageLevel.MEMORY_AND_DISK)

        # Force it to materialize
        train_pred_df.count()
        test_pred_df.count()
    
    return fitted, train_pred_df, test_pred_df


# ----------------------------------
# Model Evaluation
# ----------------------------------
def evaluate_model(
    model_name: str,
    train_pred_df: DataFrame, 
    test_pred_df: DataFrame,
    label_col: str=LABEL_COL, 
    prediction_col: str=PREDICTION_COL,
    raw_prediction_col: str=RAW_PREDICTION_COL,
    metrics: Optional[list[str]]=None,
    verbose: bool=True
) -> dict[str, dict[str, float]]:
    """
    Evaluate a binary classification model using both:

    1. BinaryClassificationEvaluator metrics:
       - areaUnderROC
       - areaUnderPR

    2. MulticlassClassificationEvaluator metrics:
       - f1
       - weightedPrecision
       - weightedRecall
       - accuracy
    """
    metric_data = {}

    if metrics is None:
        metrics = [
            "areaUnderROC",
            "areaUnderPR",
            "f1",
            "weightedPrecision",
            "weightedRecall",
            "accuracy",
        ]
    binary_metrics = {"areaUnderROC", "areaUnderPR"}
    multiclass_metrics = {
        "f1",
        "weightedPrecision",
        "weightedRecall",
        "accuracy",
    }


    # Define for each metric
    for metric in metrics:
        if metric in binary_metrics:
            evaluator = BinaryClassificationEvaluator(
                labelCol=label_col,
                rawPredictionCol=raw_prediction_col,
                metricName=metric,
            )

        elif metric in multiclass_metrics:
            evaluator = MulticlassClassificationEvaluator(
                labelCol=label_col,
                predictionCol=prediction_col,
                metricName=metric,
            )

        else:
            raise ValueError(
                f"Unsupported metric: {metric}. "
                f"Supported metrics are: {sorted(binary_metrics | multiclass_metrics)}"
            )
        
        # Compute metric
        train_score = evaluator.evaluate(train_pred_df)
        test_score = evaluator.evaluate(test_pred_df)

        if verbose:
            # Display result
            print(f"{model_name} Train {metric}: {train_score:.4f}")
            print(f"{model_name} Test {metric}: {test_score:.4f}")
            print()
    
        # Store results
        metric_data[metric] = {
            "train": train_score,
            "test": test_score,
        }

        # Memory management
        train_pred_df.unpersist()
        test_pred_df.unpersist()
        
    return metric_data