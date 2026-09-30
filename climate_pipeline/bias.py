from __future__ import annotations

import numpy as np
import xarray as xr
from scipy.stats import rankdata


def _clean(values: np.ndarray, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size < 4:
        raise ValueError(f"{label}: en az dört elemanlı tek boyutlu seri gerekli")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label}: NaN veya sonsuz değer içeriyor")
    return np.maximum(array, 0.0)


def multiplicative_qdm_1d(
    model_baseline: np.ndarray,
    reference_baseline: np.ndarray,
    target: np.ndarray,
    wet_threshold: float = 0.1,
) -> np.ndarray:
    """Multiplicative Quantile Delta Mapping for one calendar month.

    Quantile ranks are evaluated in the target distribution.  The model's
    relative change at each rank is preserved while the baseline distribution
    is mapped to the reference distribution.  An additive fallback is used
    where the model baseline quantile is effectively zero.
    """
    model = _clean(model_baseline, "Model baz dönemi")
    reference = _clean(reference_baseline, "Referans baz dönemi")
    future = _clean(target, "Hedef dönem")

    probabilities = (rankdata(future, method="average") - 0.5) / future.size
    model_q = np.quantile(model, probabilities, method="linear")
    reference_q = np.quantile(reference, probabilities, method="linear")

    corrected = np.empty_like(future)
    multiplicative = model_q > wet_threshold
    corrected[multiplicative] = (
        future[multiplicative]
        * reference_q[multiplicative]
        / model_q[multiplicative]
    )
    corrected[~multiplicative] = (
        future[~multiplicative]
        + reference_q[~multiplicative]
        - model_q[~multiplicative]
    )
    corrected[future <= wet_threshold] = 0.0
    return np.maximum(corrected, 0.0)


def monthly_qdm(
    model_baseline: xr.DataArray,
    reference_baseline: xr.DataArray,
    target: xr.DataArray,
    wet_threshold: float = 0.1,
) -> xr.DataArray:
    if model_baseline.sizes["time"] != reference_baseline.sizes["time"]:
        raise ValueError("Model ve referans baz dönem uzunlukları eşit değil")

    output = xr.full_like(target.astype(float), np.nan)
    for month in range(1, 13):
        model_month = model_baseline.where(
            model_baseline.time.dt.month == month, drop=True
        )
        reference_month = reference_baseline.where(
            reference_baseline.time.dt.month == month, drop=True
        )
        target_mask = target.time.dt.month == month
        target_month = target.where(target_mask, drop=True)
        if target_month.sizes["time"] == 0:
            continue
        corrected = multiplicative_qdm_1d(
            model_month.values,
            reference_month.values,
            target_month.values,
            wet_threshold=wet_threshold,
        )
        output.loc[{"time": target_month.time}] = corrected

    if not np.all(np.isfinite(output.values)):
        raise ValueError("Aylık QDM sonrasında eksik değer kaldı")
    output.name = "precipitation"
    output.attrs = {
        "units": "mm month-1",
        "long_name": "monthly total precipitation, bias adjusted",
        "bias_adjustment": "monthly multiplicative quantile delta mapping",
        "wet_threshold_mm_month": wet_threshold,
    }
    return output
