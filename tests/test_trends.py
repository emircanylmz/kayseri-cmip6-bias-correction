import numpy as np
import pandas as pd
import xarray as xr

from climate_pipeline.trends import (
    benjamini_hochberg,
    calculate_trend,
    seasonal_totals,
    theil_sen_line,
)


def test_djf_assigns_december_to_following_year_and_drops_partial_seasons() -> None:
    time = pd.date_range("2015-01-01", "2017-12-01", freq="MS")
    data = xr.DataArray(
        time.month.to_numpy(dtype=float), dims="time", coords={"time": time}
    )

    winter = seasonal_totals(data, (12, 1, 2))

    assert winter.index.tolist() == [2016, 2017]
    np.testing.assert_allclose(winter.values, [15.0, 15.0])


def test_theil_sen_result_and_drawn_line_use_same_slope() -> None:
    years = np.arange(2000, 2020)
    series = pd.Series(3.0 * years - 5000.0, index=years)

    result = calculate_trend(series)
    line = theil_sen_line(series, result)

    assert np.isclose(result.sen_slope, 3.0)
    np.testing.assert_allclose(np.diff(line), 3.0)


def test_benjamini_hochberg_is_bounded_and_monotonic_by_rank() -> None:
    p_values = [0.04, 0.001, 0.03, 0.2]
    adjusted = benjamini_hochberg(p_values)

    assert np.all((0.0 <= adjusted) & (adjusted <= 1.0))
    order = np.argsort(p_values)
    assert np.all(np.diff(adjusted[order]) >= 0.0)
