import numpy as np
import pandas as pd
import xarray as xr

from climate_pipeline.bias import monthly_qdm, multiplicative_qdm_1d


def test_qdm_preserves_known_multiplicative_relationship() -> None:
    time = pd.date_range("1980-01-01", "2004-12-01", freq="MS")
    baseline = xr.DataArray(
        20.0 + time.month.to_numpy() + 0.1 * (time.year.to_numpy() - 1980),
        dims="time",
        coords={"time": time},
    )
    reference = baseline * 2.0
    target_time = pd.date_range("2015-01-01", "2049-12-01", freq="MS")
    target = xr.DataArray(
        30.0 + target_time.month.to_numpy() + 0.1 * (target_time.year.to_numpy() - 2015),
        dims="time",
        coords={"time": target_time},
    )

    corrected = monthly_qdm(baseline, reference, target)

    np.testing.assert_allclose(corrected.values, target.values * 2.0)


def test_qdm_does_not_cap_future_extremes_at_reference_maximum() -> None:
    model = np.array([10.0, 20.0, 30.0, 40.0])
    reference = model * 2.0
    target = np.array([10.0, 20.0, 40.0, 100.0])

    corrected = multiplicative_qdm_1d(model, reference, target)

    assert corrected[-1] > reference.max()
    np.testing.assert_allclose(corrected, target * 2.0)


def test_qdm_handles_zero_and_tied_values() -> None:
    corrected = multiplicative_qdm_1d(
        np.array([0.0, 0.0, 2.0, 4.0, 8.0]),
        np.array([0.0, 1.0, 4.0, 8.0, 16.0]),
        np.array([0.0, 0.0, 3.0, 5.0, 12.0]),
    )

    assert np.all(np.isfinite(corrected))
    assert np.all(corrected >= 0.0)
    assert corrected[0] == corrected[1] == 0.0
