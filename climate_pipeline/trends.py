from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import xarray as xr
from scipy.stats import kendalltau, theilslopes

from .io import complete_annual_totals


@dataclass(frozen=True)
class TrendResult:
    tau: float
    p_value: float
    p_fdr: float
    sen_slope: float
    sen_low: float
    sen_high: float
    sen_intercept: float
    n: int

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def seasonal_totals(data: xr.DataArray, months: tuple[int, ...]) -> pd.Series:
    """Return complete seasonal totals; December belongs to next year's DJF."""
    series = data.to_series().dropna()
    index = pd.DatetimeIndex(series.index)
    selected = series[index.month.isin(months)]
    if selected.empty:
        return pd.Series(dtype=float)
    selected_index = pd.DatetimeIndex(selected.index)
    season_year = selected_index.year + (
        (selected_index.month == 12) & (12 in months) & (1 in months)
    ).astype(int)
    frame = pd.DataFrame({"value": selected.values, "season_year": season_year})
    grouped = frame.groupby("season_year")["value"]
    totals = grouped.sum()
    counts = grouped.count()
    return totals[counts == len(months)]


def benjamini_hochberg(p_values: list[float]) -> np.ndarray:
    values = np.asarray(p_values, dtype=float)
    order = np.argsort(values)
    ranked = values[order]
    adjusted_ranked = ranked * len(values) / np.arange(1, len(values) + 1)
    adjusted_ranked = np.minimum.accumulate(adjusted_ranked[::-1])[::-1]
    adjusted = np.empty_like(adjusted_ranked)
    adjusted[order] = np.clip(adjusted_ranked, 0.0, 1.0)
    return adjusted


def calculate_trend(series: pd.Series, p_fdr: float | None = None) -> TrendResult:
    clean = series.dropna().astype(float)
    if len(clean) < 8:
        raise ValueError("Trend için en az sekiz tam dönem gerekli")
    years = clean.index.to_numpy(dtype=float)
    values = clean.to_numpy(dtype=float)
    tau, p_value = kendalltau(years, values)
    slope, intercept, low, high = theilslopes(values, years, alpha=0.95)
    return TrendResult(
        tau=float(tau),
        p_value=float(p_value),
        p_fdr=float(p_value if p_fdr is None else p_fdr),
        sen_slope=float(slope),
        sen_low=float(low),
        sen_high=float(high),
        sen_intercept=float(intercept),
        n=len(clean),
    )


def trend_suite(data: xr.DataArray) -> tuple[dict[str, TrendResult], dict[str, pd.Series]]:
    series_by_period = {
        "Yıllık": complete_annual_totals(data),
        "Kış (DJF)": seasonal_totals(data, (12, 1, 2)),
        "İlkbahar (MAM)": seasonal_totals(data, (3, 4, 5)),
        "Yaz (JJA)": seasonal_totals(data, (6, 7, 8)),
        "Sonbahar (SON)": seasonal_totals(data, (9, 10, 11)),
    }
    initial = {name: calculate_trend(series) for name, series in series_by_period.items()}
    adjusted = benjamini_hochberg([result.p_value for result in initial.values()])
    results = {
        name: calculate_trend(series_by_period[name], float(p_adjusted))
        for (name, _), p_adjusted in zip(initial.items(), adjusted, strict=True)
    }
    return results, series_by_period


def theil_sen_line(series: pd.Series, result: TrendResult) -> np.ndarray:
    years = series.index.to_numpy(dtype=float)
    return result.sen_intercept + result.sen_slope * years
