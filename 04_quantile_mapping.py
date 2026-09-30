"""Aylık Quantile Delta Mapping uygula ve bağımsız doğrulama serisi üret."""

from __future__ import annotations

import xarray as xr

from climate_pipeline.bias import monthly_qdm
from climate_pipeline.config import CONFIG
from climate_pipeline.io import atomic_json_dump, atomic_to_netcdf, load_precipitation


def main() -> None:
    CONFIG.make_directories()
    historical = load_precipitation(CONFIG.historical_file)
    future = load_precipitation(CONFIG.future_file)
    era5 = load_precipitation(CONFIG.era5_point_file)
    historical, era5 = xr.align(historical, era5, join="exact")

    calibration_model = historical.sel(time=slice(CONFIG.historical_start, CONFIG.calibration_end))
    calibration_reference = era5.sel(time=slice(CONFIG.historical_start, CONFIG.calibration_end))
    validation_raw = historical.sel(time=slice(CONFIG.validation_start, CONFIG.historical_end))

    validation_corrected = monthly_qdm(
        calibration_model,
        calibration_reference,
        validation_raw,
        wet_threshold=CONFIG.wet_threshold_mm_month,
    )
    validation_dataset = validation_corrected.to_dataset(name="precipitation")
    validation_dataset.attrs = {
        "purpose": "independent temporal validation",
        "calibration_period": f"{CONFIG.historical_start}/{CONFIG.calibration_end}",
        "validation_period": f"{CONFIG.validation_start}/{CONFIG.historical_end}",
        "method": "monthly multiplicative quantile delta mapping",
    }
    atomic_to_netcdf(validation_dataset, CONFIG.validation_file)

    # Production mapping is refitted on the complete observed historical period.
    corrected_future = monthly_qdm(
        historical,
        era5,
        future,
        wet_threshold=CONFIG.wet_threshold_mm_month,
    )
    corrected_dataset = corrected_future.to_dataset(name="precipitation")
    corrected_dataset.attrs = {
        "source": "CMIP6",
        "model": CONFIG.model_label,
        "experiment": CONFIG.scenario,
        "reference": "ERA5 monthly averaged reanalysis",
        "baseline_period": f"{CONFIG.historical_start}/{CONFIG.historical_end}",
        "target_period": f"{CONFIG.future_start}/{CONFIG.future_end}",
        "method": "monthly multiplicative quantile delta mapping",
        "change_signal": "relative changes preserved by quantile",
    }
    atomic_to_netcdf(corrected_dataset, CONFIG.corrected_future_file)

    metadata = {
        "method": "monthly multiplicative quantile delta mapping",
        "calibration_period_for_validation": [CONFIG.historical_start, CONFIG.calibration_end],
        "independent_validation_period": [CONFIG.validation_start, CONFIG.historical_end],
        "production_baseline_period": [CONFIG.historical_start, CONFIG.historical_end],
        "projection_period": [CONFIG.future_start, CONFIG.future_end],
        "wet_threshold_mm_month": CONFIG.wet_threshold_mm_month,
        "notes": [
            "Her takvim ayı ayrı düzeltilir.",
            "Gelecek değerler historical maksimumda kırpılmaz.",
            "Tek model/tek senaryo belirsizliği ayrıca değerlendirilmelidir.",
        ],
    }
    atomic_json_dump(metadata, CONFIG.result_dir / "qdm_metadata.json")

    print(
        f"Bağımsız doğrulama serisi: {CONFIG.validation_file}\n"
        f"Düzeltilmiş SSP245 serisi: {CONFIG.corrected_future_file}\n"
        "Sıradaki adım: 05_dogrulama_metrikleri.py"
    )


if __name__ == "__main__":
    main()
