from __future__ import annotations

import zipfile

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from climate_pipeline.io import (
    convert_precipitation_to_mm_month,
    normalise_and_validate_monthly_time,
    open_point_series,
    safe_extract_zip,
)


def test_point_interpolation_and_cmip_unit_conversion(tmp_path) -> None:
    time = pd.date_range("2000-01-01", periods=2, freq="MS")
    values = np.ones((2, 2, 2)) / 86400.0
    dataset = xr.Dataset(
        {
            "pr": (
                ("time", "lat", "lon"),
                values,
                {"units": "kg m-2 s-1"},
            )
        },
        coords={"time": time, "lat": [38.0, 39.0], "lon": [35.0, 36.0]},
    )
    path = tmp_path / "cmip.nc"
    dataset.to_netcdf(path)

    point = open_point_series([path], ("pr",), 38.5, 35.5)
    converted = convert_precipitation_to_mm_month(point, "cmip6")
    validated = normalise_and_validate_monthly_time(
        converted, "2000-01-01", "2000-02-01", "test"
    )

    np.testing.assert_allclose(validated.values, [31.0, 29.0])


def test_monthly_time_validation_rejects_missing_month() -> None:
    data = xr.DataArray(
        [1.0, 2.0],
        dims="time",
        coords={"time": pd.to_datetime(["2000-01-01", "2000-03-01"])},
    )
    with pytest.raises(ValueError, match="uyuşmuyor"):
        normalise_and_validate_monthly_time(
            data, "2000-01-01", "2000-03-01", "eksik"
        )


def test_safe_extract_rejects_path_traversal(tmp_path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("../outside.nc", "not-a-netcdf")

    with pytest.raises(ValueError, match="Güvensiz ZIP"):
        safe_extract_zip(archive, tmp_path / "output")
