"""CDS'den bölgesel CMIP6 ve ERA5 aylık yağış verilerini indir."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import cdsapi

from climate_pipeline.config import CONFIG
from climate_pipeline.io import atomic_json_dump


MONTHS = [f"{month:02d}" for month in range(1, 13)]


def download(
    client: cdsapi.Client,
    dataset: str,
    request: dict[str, object],
    target: Path,
    force: bool,
) -> None:
    if target.exists() and target.stat().st_size > 0 and not force:
        print(f"Atlandı (zaten var): {target}")
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.part")
    temporary.unlink(missing_ok=True)
    print(f"İndiriliyor: {target.name}")
    try:
        client.retrieve(dataset, request, str(temporary))
        if not temporary.exists() or temporary.stat().st_size == 0:
            raise RuntimeError(f"CDS boş dosya döndürdü: {target.name}")
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    print(f"Tamamlandı: {target} ({target.stat().st_size / 1024**2:.1f} MB)")


def build_requests() -> dict[str, dict[str, object]]:
    common_cmip = {
        "temporal_resolution": "monthly",
        "variable": "precipitation",
        "model": CONFIG.model,
        "month": MONTHS,
        "area": list(CONFIG.download_area),
    }
    return {
        "historical": {
            **common_cmip,
            "experiment": "historical",
            "year": [str(year) for year in range(1980, 2015)],
        },
        "future": {
            **common_cmip,
            "experiment": CONFIG.scenario,
            "year": [str(year) for year in range(2015, 2050)],
        },
        "era5": {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": ["total_precipitation"],
            "year": [str(year) for year in range(1980, 2015)],
            "month": MONTHS,
            "time": ["00:00"],
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": list(CONFIG.download_area),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Mevcut indirmeleri yenile")
    args = parser.parse_args()

    CONFIG.make_directories()
    requests = build_requests()
    atomic_json_dump(requests, CONFIG.raw_dir / "download_requests.json")

    print("CDS indirmeleri başlıyor. Veri kümesi lisansları önceden kabul edilmiş olmalı.")
    client = cdsapi.Client()
    download(
        client,
        "projections-cmip6",
        requests["historical"],
        CONFIG.historical_archive,
        args.force,
    )
    download(
        client,
        "projections-cmip6",
        requests["future"],
        CONFIG.future_archive,
        args.force,
    )
    download(
        client,
        "reanalysis-era5-single-levels-monthly-means",
        requests["era5"],
        CONFIG.era5_file,
        args.force,
    )
    print("İndirmeler tamamlandı. Sıradaki adım: 02_zip_ac.py")


if __name__ == "__main__":
    main()
