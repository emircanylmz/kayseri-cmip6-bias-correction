from __future__ import annotations

import json
import os
import tempfile
import zipfile
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


TIME_NAMES = ("time", "valid_time", "date")
LAT_NAMES = ("lat", "latitude")
LON_NAMES = ("lon", "longitude")


def atomic_json_dump(payload: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def atomic_to_netcdf(dataset: xr.Dataset, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".nc", dir=path.parent
    )
    os.close(fd)
    try:
        dataset.to_netcdf(tmp_name)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def safe_extract_zip(archive: Path, destination: Path, force: bool = False) -> list[Path]:
    """Extract an archive without allowing members to escape destination."""
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    extracted: list[Path] = []

    with zipfile.ZipFile(archive) as zipped:
        for info in zipped.infolist():
            target = (destination / info.filename).resolve()
            if target != destination_root and destination_root not in target.parents:
                raise ValueError(f"Güvensiz ZIP yolu reddedildi: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if force or not target.exists() or target.stat().st_size != info.file_size:
                with zipped.open(info) as source, target.open("wb") as sink:
                    while chunk := source.read(1024 * 1024):
                        sink.write(chunk)
            extracted.append(target)
    return extracted


def find_netcdf_files(path: Path) -> list[Path]:
    files = sorted(p for p in path.rglob("*.nc") if p.is_file())
    if not files:
        raise FileNotFoundError(f"NetCDF bulunamadı: {path}")
    return files


def _first_existing(names: Iterable[str], available: Iterable[str], kind: str) -> str:
    available_set = set(available)
    for name in names:
        if name in available_set:
            return name
    raise ValueError(f"{kind} bulunamadı. Mevcut adlar: {sorted(available_set)}")


def _drop_or_reject_extra_dimensions(
    data: xr.DataArray, allowed: set[str]
) -> xr.DataArray:
    for dim in tuple(data.dims):
        if dim in allowed:
            continue
        if data.sizes[dim] != 1:
            raise ValueError(
                f"Beklenmeyen çok elemanlı boyut {dim!r}={data.sizes[dim]}. "
                "Model üyesi/level açıkça seçilmeli."
            )
        data = data.isel({dim: 0}, drop=True)
    return data


def _normalise_longitude(data: xr.DataArray, lon_name: str) -> xr.DataArray:
    longitude = data[lon_name]
    if float(longitude.max()) > 180.0:
        data = data.assign_coords(
            {lon_name: ((longitude + 180.0) % 360.0) - 180.0}
        )
    return data.sortby(lon_name)


def _extract_point_from_file(
    path: Path,
    variable_names: tuple[str, ...],
    latitude: float,
    longitude: float,
) -> xr.DataArray:
    with xr.open_dataset(path, decode_times=True, use_cftime=True) as dataset:
        variable = _first_existing(variable_names, dataset.data_vars, "Yağış değişkeni")
        time_name = _first_existing(TIME_NAMES, dataset.coords, "Zaman koordinatı")
        lat_name = _first_existing(LAT_NAMES, dataset.coords, "Enlem koordinatı")
        lon_name = _first_existing(LON_NAMES, dataset.coords, "Boylam koordinatı")

        data = dataset[variable]
        data = _drop_or_reject_extra_dimensions(
            data, {time_name, lat_name, lon_name}
        )
        data = _normalise_longitude(data, lon_name).sortby(lat_name)

        lat_values = np.asarray(data[lat_name].values, dtype=float)
        lon_values = np.asarray(data[lon_name].values, dtype=float)
        if not (lat_values.min() <= latitude <= lat_values.max()):
            raise ValueError(f"{path.name}: hedef enlem veri alanının dışında")
        if not (lon_values.min() <= longitude <= lon_values.max()):
            raise ValueError(f"{path.name}: hedef boylam veri alanının dışında")

        # Both sources are brought to exactly the same target coordinate.
        point = data.interp({lat_name: latitude, lon_name: longitude}, method="linear")
        if time_name != "time":
            point = point.rename({time_name: "time"})
        point = point.drop_vars([lat_name, lon_name], errors="ignore").load()
        point.attrs = dict(data.attrs)
        for attribute in (
            "source_id",
            "experiment_id",
            "variant_label",
            "grid_label",
            "institution_id",
        ):
            value = dataset.attrs.get(attribute)
            if value is not None:
                point.attrs[attribute] = value
        calendar = dataset[time_name].encoding.get("calendar")
        if calendar:
            point.attrs["source_calendar"] = calendar
        return point


def open_point_series(
    paths: Iterable[Path],
    variable_names: tuple[str, ...],
    latitude: float,
    longitude: float,
) -> xr.DataArray:
    arrays = [
        _extract_point_from_file(path, variable_names, latitude, longitude)
        for path in sorted(paths)
    ]
    combined = xr.concat(arrays, dim="time") if len(arrays) > 1 else arrays[0]
    combined = combined.sortby("time")

    year_month = np.array(
        [
            int(year) * 100 + int(month)
            for year, month in zip(
                combined.time.dt.year.values,
                combined.time.dt.month.values,
                strict=True,
            )
        ]
    )
    _, unique_indices = np.unique(year_month, return_index=True)
    if len(unique_indices) != combined.sizes["time"]:
        combined = combined.isel(time=np.sort(unique_indices))
    return combined


def convert_precipitation_to_mm_month(
    data: xr.DataArray, source: str
) -> xr.DataArray:
    source = source.lower()
    units = str(data.attrs.get("units", "")).lower().replace("**", "^")
    days = data.time.dt.days_in_month.astype(float)

    if source == "cmip6":
        recognised = (
            "kg m-2 s-1",
            "kg m^-2 s^-1",
            "kg/m2/s",
            "kg m-2 s-1",
        )
        if units and not any(token in units for token in recognised):
            raise ValueError(f"Beklenmeyen CMIP6 yağış birimi: {units!r}")
        converted = data.astype(float) * 86400.0 * days
    elif source == "era5":
        # In the requested monthly-averaged ERA5 product, accumulated fields
        # are expressed as the mean daily accumulation (metres/day).
        if units and units not in {"m", "m of water equivalent"}:
            raise ValueError(f"Beklenmeyen ERA5 yağış birimi: {units!r}")
        converted = data.astype(float) * 1000.0 * days
    else:
        raise ValueError(f"Bilinmeyen kaynak: {source}")

    converted.attrs = {
        **data.attrs,
        "units": "mm month-1",
        "long_name": "monthly total precipitation",
        "source_product": source,
    }
    return converted


def normalise_and_validate_monthly_time(
    data: xr.DataArray, start: str, end: str, label: str
) -> xr.DataArray:
    expected = pd.date_range(start, end, freq="MS")
    observed_pairs = list(
        zip(
            np.asarray(data.time.dt.year.values, dtype=int),
            np.asarray(data.time.dt.month.values, dtype=int),
            strict=True,
        )
    )
    expected_pairs = list(zip(expected.year, expected.month, strict=True))
    if observed_pairs != expected_pairs:
        missing = sorted(set(expected_pairs) - set(observed_pairs))
        extra = sorted(set(observed_pairs) - set(expected_pairs))
        raise ValueError(
            f"{label}: aylık zaman ekseni beklenen dönemle uyuşmuyor. "
            f"Eksik={missing[:6]}, fazla={extra[:6]}"
        )
    values = np.asarray(data.values, dtype=float)
    if values.ndim != 1:
        raise ValueError(f"{label}: seri tek boyutlu değil: {values.shape}")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{label}: NaN veya sonsuz değer içeriyor")
    tolerance = 1e-8
    if np.any(values < -tolerance):
        raise ValueError(f"{label}: negatif yağış değerleri içeriyor")
    values = np.maximum(values, 0.0)
    result = xr.DataArray(
        values,
        dims="time",
        coords={"time": expected},
        name="precipitation",
        attrs=dict(data.attrs),
    )
    return result


def point_dataset(
    data: xr.DataArray,
    *,
    source: str,
    experiment: str,
    model: str,
    latitude: float,
    longitude: float,
    input_files: Iterable[Path],
) -> xr.Dataset:
    dataset = data.to_dataset(name="precipitation")
    dataset.attrs = {
        "source": source,
        "experiment": experiment,
        "model": model,
        "target_latitude": latitude,
        "target_longitude": longitude,
        "spatial_method": "bilinear interpolation to target coordinate",
        "input_files": ", ".join(str(path) for path in input_files),
    }
    for attribute in (
        "source_id",
        "experiment_id",
        "variant_label",
        "grid_label",
        "institution_id",
        "source_calendar",
    ):
        value = data.attrs.get(attribute)
        if value is not None:
            dataset.attrs[attribute] = value
    return dataset


def load_precipitation(path: Path) -> xr.DataArray:
    if not path.exists():
        raise FileNotFoundError(f"Gerekli dosya bulunamadı: {path}")
    with xr.open_dataset(path) as dataset:
        if "precipitation" not in dataset:
            raise ValueError(f"{path}: precipitation değişkeni yok")
        data = dataset["precipitation"].load()
        data.attrs = dict(dataset["precipitation"].attrs)
        return data


def complete_annual_totals(data: xr.DataArray) -> pd.Series:
    series = data.to_series()
    grouped = series.groupby(series.index.year)
    totals = grouped.sum()
    counts = grouped.count()
    return totals[counts == 12]


def monthly_climatology(data: xr.DataArray) -> pd.Series:
    series = data.to_series()
    return series.groupby(series.index.month).mean().reindex(range(1, 13))
