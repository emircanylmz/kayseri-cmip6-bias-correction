"""CMIP6 arşivlerini güvenli biçimde aç ve veri manifestini oluştur."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from climate_pipeline.config import CONFIG
from climate_pipeline.io import atomic_json_dump, find_netcdf_files, safe_extract_zip


def extract(archive: Path, destination: Path, force: bool) -> list[Path]:
    if not archive.exists():
        raise FileNotFoundError(f"Arşiv bulunamadı: {archive}. Önce 01_veri_indir.py çalıştırın.")
    if not zipfile.is_zipfile(archive):
        raise ValueError(f"Beklenen ZIP biçiminde değil: {archive}")
    safe_extract_zip(archive, destination, force=force)
    files = find_netcdf_files(destination)
    print(f"{archive.name}: {len(files)} NetCDF hazır")
    return files


def relative_paths(paths: list[Path]) -> list[str]:
    return [str(path.relative_to(CONFIG.project_root)) for path in paths]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Çıkarılmış dosyaları yenile")
    args = parser.parse_args()

    CONFIG.make_directories()
    historical_dir = CONFIG.raw_dir / "cmip6_historical"
    future_dir = CONFIG.raw_dir / "cmip6_ssp245"
    historical_files = extract(CONFIG.historical_archive, historical_dir, args.force)
    future_files = extract(CONFIG.future_archive, future_dir, args.force)
    if not CONFIG.era5_file.exists() or CONFIG.era5_file.stat().st_size == 0:
        raise FileNotFoundError(f"ERA5 dosyası bulunamadı: {CONFIG.era5_file}")

    manifest = {
        "cmip6_historical": relative_paths(historical_files),
        "cmip6_ssp245": relative_paths(future_files),
        "era5": str(CONFIG.era5_file.relative_to(CONFIG.project_root)),
    }
    atomic_json_dump(manifest, CONFIG.manifest_file)
    print(f"Manifest yazıldı: {CONFIG.manifest_file}")
    print("Sıradaki adım: 03_veri_kontrol.py")


if __name__ == "__main__":
    main()
