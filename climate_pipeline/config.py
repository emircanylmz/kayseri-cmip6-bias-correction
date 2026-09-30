from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class PipelineConfig:
    project_root: Path = PROJECT_ROOT
    latitude: float = 38.73
    longitude: float = 35.48
    model: str = "mpi_esm1_2_lr"
    model_label: str = "MPI-ESM1-2-LR"
    scenario: str = "ssp2_4_5"
    historical_start: str = "1980-01-01"
    calibration_end: str = "2004-12-31"
    validation_start: str = "2005-01-01"
    historical_end: str = "2014-12-31"
    future_start: str = "2015-01-01"
    future_end: str = "2049-12-31"
    # CDS area order: north, west, south, east.  The margin is deliberately
    # wider than a single GCM cell so bilinear interpolation remains possible.
    download_area: tuple[float, float, float, float] = (42.0, 31.0, 35.0, 40.0)
    wet_threshold_mm_month: float = 0.1

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def figure_dir(self) -> Path:
        return self.project_root / "gorseller"

    @property
    def result_dir(self) -> Path:
        return self.project_root / "sonuclar"

    @property
    def historical_archive(self) -> Path:
        return self.raw_dir / "cmip6_historical_1980_2014.zip"

    @property
    def future_archive(self) -> Path:
        return self.raw_dir / "cmip6_ssp245_2015_2049.zip"

    @property
    def era5_file(self) -> Path:
        return self.raw_dir / "era5_monthly_1980_2014.nc"

    @property
    def manifest_file(self) -> Path:
        return self.raw_dir / "manifest.json"

    @property
    def historical_file(self) -> Path:
        return self.processed_dir / "cmip6_historical_kayseri.nc"

    @property
    def future_file(self) -> Path:
        return self.processed_dir / "cmip6_ssp245_kayseri.nc"

    @property
    def era5_point_file(self) -> Path:
        return self.processed_dir / "era5_kayseri.nc"

    @property
    def corrected_future_file(self) -> Path:
        return self.processed_dir / "cmip6_ssp245_qdm_kayseri.nc"

    @property
    def validation_file(self) -> Path:
        return self.processed_dir / "validation_qdm_kayseri.nc"

    def make_directories(self) -> None:
        for path in (
            self.raw_dir,
            self.processed_dir,
            self.figure_dir,
            self.result_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


CONFIG = PipelineConfig()
