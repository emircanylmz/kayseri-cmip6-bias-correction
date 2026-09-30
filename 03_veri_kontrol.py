"""NetCDF'leri doğrula, Kayseri noktasına enterpole et ve mm/ay'a dönüştür."""

from __future__ import annotations

import json
from pathlib import Path

import xarray as xr

from climate_pipeline.config import CONFIG
from climate_pipeline.io import (
    atomic_to_netcdf,
    convert_precipitation_to_mm_month,
    normalise_and_validate_monthly_time,
    open_point_series,
    point_dataset,
)


def load_manifest() -> tuple[list[Path], list[Path], Path]:
    if not CONFIG.manifest_file.exists():
        raise FileNotFoundError(
            f"Manifest bulunamadı: {CONFIG.manifest_file}. Önce 02_zip_ac.py çalıştırın."
        )
    payload = json.loads(CONFIG.manifest_file.read_text(encoding="utf-8"))
    historical = [CONFIG.project_root / item for item in payload["cmip6_historical"]]
    future = [CONFIG.project_root / item for item in payload["cmip6_ssp245"]]
    era5 = CONFIG.project_root / payload["era5"]
    missing = [path for path in [*historical, *future, era5] if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Manifestte olup diskte bulunmayan dosyalar: {missing}")
    return historical, future, era5


def prepare(
    paths: list[Path],
    variable_names: tuple[str, ...],
    source: str,
    start: str,
    end: str,
    label: str,
) -> xr.DataArray:
    point = open_point_series(
        paths,
        variable_names,
        CONFIG.latitude,
        CONFIG.longitude,
    )
    monthly = convert_precipitation_to_mm_month(point, source)
    return normalise_and_validate_monthly_time(monthly, start, end, label)


def save_series(
    data: xr.DataArray,
    path: Path,
    source: str,
    experiment: str,
    model: str,
    inputs: list[Path],
) -> None:
    dataset = point_dataset(
        data,
        source=source,
        experiment=experiment,
        model=model,
        latitude=CONFIG.latitude,
        longitude=CONFIG.longitude,
        input_files=inputs,
    )
    atomic_to_netcdf(dataset, path)
    print(
        f"{path.name}: {data.sizes['time']} ay, "
        f"{float(data.mean()) * 12:.1f} mm/yıl"
    )


def main() -> None:
    CONFIG.make_directories()
    historical_paths, future_paths, era5_path = load_manifest()

    print(f"Ortak hedef koordinat: {CONFIG.latitude:.2f}°K, {CONFIG.longitude:.2f}°D")
    historical = prepare(
        historical_paths,
        ("pr", "precipitation"),
        "cmip6",
        CONFIG.historical_start,
        CONFIG.historical_end,
        "CMIP6 historical",
    )
    future = prepare(
        future_paths,
        ("pr", "precipitation"),
        "cmip6",
        CONFIG.future_start,
        CONFIG.future_end,
        "CMIP6 SSP245",
    )
    era5 = prepare(
        [era5_path],
        ("tp", "total_precipitation", "precipitation"),
        "era5",
        CONFIG.historical_start,
        CONFIG.historical_end,
        "ERA5",
    )
    xr.align(historical, era5, join="exact")

    save_series(
        historical,
        CONFIG.historical_file,
        "CMIP6",
        "historical",
        CONFIG.model_label,
        historical_paths,
    )
    save_series(
        future,
        CONFIG.future_file,
        "CMIP6",
        CONFIG.scenario,
        CONFIG.model_label,
        future_paths,
    )
    save_series(
        era5,
        CONFIG.era5_point_file,
        "ERA5 reanalysis",
        "monthly_averaged_reanalysis",
        "ERA5",
        [era5_path],
    )
    print("Ön işleme tamamlandı. Sıradaki adım: 04_quantile_mapping.py")


if __name__ == "__main__":
    main()
