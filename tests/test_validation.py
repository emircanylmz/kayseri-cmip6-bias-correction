import numpy as np
import pandas as pd
import xarray as xr

from climate_pipeline.validation import metrics_table


def test_corrected_series_improves_distribution_metrics() -> None:
    time = pd.date_range("2005-01-01", "2014-12-01", freq="MS")
    observed = xr.DataArray(
        30.0 + time.month.to_numpy(dtype=float),
        dims="time",
        coords={"time": time},
    )
    raw = observed * 1.5
    corrected = observed.copy()

    table = metrics_table(raw, corrected, observed)

    assert abs(table.loc["PBIAS (%)", "CMIP6 QDM"]) < abs(
        table.loc["PBIAS (%)", "CMIP6 ham"]
    )
    assert table.loc["Wasserstein uzaklığı (mm/ay)", "CMIP6 QDM"] == 0.0
