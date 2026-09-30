from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr
from scipy.stats import ks_2samp, wasserstein_distance

from .io import complete_annual_totals, monthly_climatology


def _pbias(simulated: np.ndarray, observed: np.ndarray) -> float:
    denominator = float(np.mean(observed))
    if np.isclose(denominator, 0.0):
        return np.nan
    return 100.0 * (float(np.mean(simulated)) - denominator) / denominator


def validation_metrics(
    simulated: xr.DataArray, observed: xr.DataArray
) -> dict[str, float]:
    simulated, observed = xr.align(simulated, observed, join="exact")
    sim = np.asarray(simulated.values, dtype=float)
    obs = np.asarray(observed.values, dtype=float)
    if not np.all(np.isfinite(sim)) or not np.all(np.isfinite(obs)):
        raise ValueError("Doğrulama serileri sonlu değerlerden oluşmalı")

    sim_clim = monthly_climatology(simulated).values
    obs_clim = monthly_climatology(observed).values
    annual_sim = complete_annual_totals(simulated)
    annual_obs = complete_annual_totals(observed)
    annual_sim, annual_obs = annual_sim.align(annual_obs, join="inner")

    return {
        "Ortalama (mm/ay)": float(np.mean(sim)),
        "Standart sapma (mm/ay)": float(np.std(sim, ddof=1)),
        "PBIAS (%)": _pbias(sim, obs),
        "Aylık klimatoloji RMSE (mm/ay)": float(
            np.sqrt(np.mean((sim_clim - obs_clim) ** 2))
        ),
        "Aylık klimatoloji MAE (mm/ay)": float(
            np.mean(np.abs(sim_clim - obs_clim))
        ),
        "Wasserstein uzaklığı (mm/ay)": float(wasserstein_distance(sim, obs)),
        "KS istatistiği": float(ks_2samp(sim, obs).statistic),
        "Q95 farkı (mm/ay)": float(np.quantile(sim, 0.95) - np.quantile(obs, 0.95)),
        "Yıllık ortalama (mm/yıl)": float(annual_sim.mean()),
        "Yıllık ortalama farkı (mm/yıl)": float(
            annual_sim.mean() - annual_obs.mean()
        ),
    }


def metrics_table(
    raw: xr.DataArray, corrected: xr.DataArray, observed: xr.DataArray
) -> pd.DataFrame:
    raw_metrics = validation_metrics(raw, observed)
    corrected_metrics = validation_metrics(corrected, observed)
    observed_metrics = validation_metrics(observed, observed)
    return pd.DataFrame(
        {
            "ERA5 referans": observed_metrics,
            "CMIP6 ham": raw_metrics,
            "CMIP6 QDM": corrected_metrics,
        }
    )
