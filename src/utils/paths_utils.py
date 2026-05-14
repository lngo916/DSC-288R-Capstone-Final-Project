from __future__ import annotations

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
            return Path("/Users/steveg/Downloads")

        raise ValueError(f"Unsupported mode: {self.mode}")

    @property
    def raw_csv_root(self) -> Path:
        return self.data_root / "raw_csv"
    
    @property
    def full_parquet(self) -> Path:
        return self.data_root / "full_parquet"
    
    @property
    def cleaned_parquet(self) -> Path:
        return self.data_root / "cleaned_parquet"

    @property
    def sampled_parquet(self) -> Path:
        return self.data_root / "subsampled_parquet"

    @property
    def cleaned_sample_parquet(self) -> Path:
        return self.data_root / "cleaned_sampled.parquet"
    
    @property
    def train_sample_parquet(self) -> Path:
        return self.data_root / "train_sampled.parquet"
    
    @property
    def validate_sample_parquet(self) -> Path:
        return self.data_root / "validate_sampled.parquet"
    
    @property
    def test_sample_parquet(self) -> Path:
        return self.data_root / "test_sampled.parquet"
    
    # ------------------------------------------------------------------
    # Spark path helpers, used for writing parquet files in Spark
    # ------------------------------------------------------------------
    def spark_path(self, path: str | Path) -> str:
        """
        Convert a normal filesystem path into a Spark-readable local file path.

        For Expanse Spark reads/writes, use file:/...
        For Colab/Local, plain paths usually work.
        """
        path = Path(path)

        if self.mode_upper == "EXPANSE":
            return f"file:{path}"

        return str(path)

    @property
    def full_parquet_spark(self) -> str:
        return self.spark_path(self.full_parquet)

    @property
    def sampled_parquet_spark(self) -> str:
        return self.spark_path(self.sampled_parquet)

    @property
    def cleaned_sample_parquet_spark(self) -> str:
        return self.spark_path(self.cleaned_sample_parquet)