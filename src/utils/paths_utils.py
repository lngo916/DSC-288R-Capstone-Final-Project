from dataclasses import dataclass
from pathlib import Path


VALID_MODES = {"COLAB", "LOCAL", "EXPANSE"}


@dataclass(frozen=True)
class ProjectPaths:
    """
    Centralized project path configuration.

    This class does NOT modify sys.path.
    Notebook bootstrap code is responsible for:
    - setting MODE
    - mounting Google Drive if needed
    - adding project root to sys.path
    """

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    mode: str

    def __post_init__(self):
        mode = self.mode.upper()
        if mode not in VALID_MODES:
            raise ValueError(
                f"Invalid mode: {self.mode}. "
                f"Expected one of: {sorted(VALID_MODES)}"
            )

    @property
    def mode_upper(self) -> str:
        return self.mode.upper()


    # ------------------------------------------------------------------
    # Data roots
    # ------------------------------------------------------------------
    @property
    def data_root(self) -> Path:
        """
        Root directory for data storage.

        On Expanse, keep large data on Lustre scratch, not in HOME.
        On Colab/Local, data can live inside the project folder.
        """
        if self.mode_upper == "EXPANSE":
            return Path("/expanse/lustre/scratch/bguo3/temp_project/steam_reviews")

        if self.mode_upper == "COLAB":
            return Path("/content/drive/MyDrive/DSC 288R/Project/data")

        if self.mode_upper == "LOCAL":
            return Path("/Users/steveg/Desktop/DSC-288R-Capstone-Final-Project")

        raise ValueError(f"Unsupported mode: {self.mode}")


    # ------------------------------------------------------------------
    # Original datasets
    # ------------------------------------------------------------------
    @property
    def raw_csv_root(self) -> Path:
        return self.data_root / "raw_csv"
    

    # ------------------------------------------------------------------
    # Full datasets
    # ------------------------------------------------------------------
    @property
    def full_parquet(self) -> Path:
        return self.data_root / "full_parquet"
    
    @property
    def cleaned_parquet(self) -> Path:
        return self.data_root / "cleaned_parquet"

    @property
    def feature_engineered_parquet(self) -> Path:
        return self.data_root / "feature_engineered_parquet"


    # ------------------------------------------------------------------
    # Sampled datasets
    # ------------------------------------------------------------------
    @property
    def sampled_parquet(self) -> Path:
        return self.data_root / "subsampled_parquet"

    @property
    def cleaned_sampled_parquet(self) -> Path:
        return self.data_root / "cleaned_sampled_parquet"

    @property
    def feature_engineered_sampled_parquet(self) -> Path:
        return self.data_root / "feature_engineered_sampled_parquet"
    

    # ------------------------------------------------------------------
    # Train / validation / test split datasets FOR FULL
    # ------------------------------------------------------------------
    # Split data root
    @property
    def splits_root(self) -> Path:
        return self.data_root / "train_val_test_splits"

    @property
    def random_row_split_root(self) -> Path:
        return self.splits_root / "random_row"

    @property
    def random_user_split_root(self) -> Path:
        return self.splits_root / "random_user"

    @property
    def time_aware_row_split_root(self) -> Path:
        return self.splits_root / "time_aware_row"

    # Random row split paths
    @property
    def random_row_train_parquet(self) -> Path:
        return self.random_row_split_root / "train_parquet"

    @property
    def random_row_val_parquet(self) -> Path:
        return self.random_row_split_root / "val_parquet"

    @property
    def random_row_test_parquet(self) -> Path:
        return self.random_row_split_root / "test_parquet"

    # Random user split paths
    @property
    def random_user_train_parquet(self) -> Path:
        return self.random_user_split_root / "train_parquet"

    @property
    def random_user_val_parquet(self) -> Path:
        return self.random_user_split_root / "val_parquet"

    @property
    def random_user_test_parquet(self) -> Path:
        return self.random_user_split_root / "test_parquet"

    # Time-aware row split paths
    @property
    def time_aware_row_train_parquet(self) -> Path:
        return self.time_aware_row_split_root / "train_parquet"

    @property
    def time_aware_row_val_parquet(self) -> Path:
        return self.time_aware_row_split_root / "val_parquet"

    @property
    def time_aware_row_test_parquet(self) -> Path:
        return self.time_aware_row_split_root / "test_parquet"
    
    
    # # ------------------------------------------------------------------
    # # Train / validation / test split datasets FOR SAMPLED
    # # ------------------------------------------------------------------
    # Random row split sampled paths
    @property
    def random_row_train_sampled_parquet(self) -> Path:
        return self.random_row_split_root / "train_sampled_parquet"

    @property
    def random_row_val_sampled_parquet(self) -> Path:
        return self.random_row_split_root / "val_sampled_parquet"

    @property
    def random_row_test_sampled_parquet(self) -> Path:
        return self.random_row_split_root / "test_sampled_parquet"

    
    # # ------------------------------------------------------------------
    # # Spark path helpers, used for writing parquet files in Spark
    # # ------------------------------------------------------------------
    # def spark_path(self, path: str | Path) -> str:
    #     """
    #     Convert a normal filesystem path into a Spark-readable local file path.

    #     For Expanse Spark reads/writes, use file:/...
    #     For Colab/Local, plain paths usually work.
    #     """
    #     path = Path(path)

    #     if self.mode_upper == "EXPANSE":
    #         return f"file:{path}"

    #     return str(path)

    # @property
    # def full_parquet_spark(self) -> str:
    #     return self.spark_path(self.full_parquet)

    # @property
    # def cleaned_parquet_spark(self) -> str:
    #     return self.spark_path(self.cleaned_parquet)
    
    # @property
    # def feature_engineered_parquet_spark(self) -> str:
    #     return self.spark_path(self.feature_engineered_parquet)

    # @property
    # def sampled_parquet_spark(self) -> str:
    #     return self.spark_path(self.sampled_parquet)

    # @property
    # def cleaned_sampled_parquet_spark(self) -> str:
    #     return self.spark_path(self.cleaned_sampled_parquet)
    
    # @property
    # def feature_engineered_sampled_parquet_spark(self) -> str:
    #     return self.spark_path(self.feature_engineered_sampled_parquet)
    
    # # ------------------------------------------------------------------
    # # Spark split output paths
    # # ------------------------------------------------------------------
    # @property
    # def random_row_train_parquet_spark(self) -> str:
    #     return self.spark_path(self.random_row_train_parquet)

    # @property
    # def random_row_val_parquet_spark(self) -> str:
    #     return self.spark_path(self.random_row_val_parquet)

    # @property
    # def random_row_test_parquet_spark(self) -> str:
    #     return self.spark_path(self.random_row_test_parquet)

    # @property
    # def random_user_train_parquet_spark(self) -> str:
    #     return self.spark_path(self.random_user_train_parquet)

    # @property
    # def random_user_val_parquet_spark(self) -> str:
    #     return self.spark_path(self.random_user_val_parquet)

    # @property
    # def random_user_test_parquet_spark(self) -> str:
    #     return self.spark_path(self.random_user_test_parquet)

    # @property
    # def time_aware_row_train_parquet_spark(self) -> str:
    #     return self.spark_path(self.time_aware_row_train_parquet)

    # @property
    # def time_aware_row_val_parquet_spark(self) -> str:
    #     return self.spark_path(self.time_aware_row_val_parquet)

    # @property
    # def time_aware_row_test_parquet_spark(self) -> str:
    #     return self.spark_path(self.time_aware_row_test_parquet)