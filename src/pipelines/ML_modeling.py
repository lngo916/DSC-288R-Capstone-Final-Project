# -----------------------------
# Import Modules
# -----------------------------
# Spark
from pyspark import StorageLevel

# ML
from pyspark.ml.classification import (
    LogisticRegression, 
    DecisionTreeClassifier,
    RandomForestClassifier,
    LinearSVC
)
from xgboost.spark import SparkXGBClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator


# -----------------------------
# ML constants
# -----------------------------
# For XGBoost param setup
NUM_EXECUTORS = int(sc.getConf().get("spark.executor.instances", "1"))
EXECUTOR_CORES = int(sc.getConf().get("spark.executor.cores", "1"))
TOTAL_CORES = NUM_EXECUTORS * EXECUTOR_CORES

# For feature names
FEATURE_COL = "finalized_features"
LABEL_COL = "churn"

# ----------------------------------
# Model Definition
# ----------------------------------
MODELS = {
    "log_reg": LogisticRegression(
        featuresCol=FEATURE_COL,
        labelCol=LABEL_COL
    ),

    "decision_tree": DecisionTreeClassifier(
        featuresCol='features', 
        labelCol='label'
        
    "random_forest": RandomForestClassifier(
        featuresCol=FEATURE_COL,
        labelCol=LABEL_COL
    ),

    "svm": LinearSVC(
        featuresCol=FEATURE_COL,
        labelCol=LABEL_COL
    ),

    "xgb": SparkXGBClassifier(
        features_col=FEATURE_COL,
        label_col=LABEL_COL,
        prediction_col=PREDICTION_COL,
        num_workers=TOTAL_CORES
    ),
}


# ----------------------------------
# Model Fit & Transform
# ----------------------------------
def fit_transform_model(
    model_name,
    train_final_df,
    test_final_df,
    cache=False
):
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
    model_name,
    train_pred_df, 
    test_pred_df,
    label_col=LABEL_COL, 
    metrics=["f1", "weightedPrecision", "weightedRecall", "accuracy"],
    verbose=True
):
    metric_data = {}
    
    # Define for each metric
    for metric in metrics:
        evaluator = BinaryClassificationEvaluator(
            rawPredictionCol=PREDICTION_COL,
            labelCol=label_col,
            metricName=metric
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
        metric_data[metric] = [train_score, test_score]
    return metric_data