"""Kalibrasyon, projeksiyon, mevsimsellik ve doğrulama Q-Q grafiklerini üret."""

from __future__ import annotations

import os

from climate_pipeline.config import CONFIG

os.environ.setdefault("MPLCONFIGDIR", str(CONFIG.project_root / ".cache" / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np

from climate_pipeline.io import (
    complete_annual_totals,
    load_precipitation,
    monthly_climatology,
)


MONTH_LABELS = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
COLORS = {
    "era5": "#1976D2",
    "historical": "#D32F2F",
    "future": "#F57C00",
    "corrected": "#388E3C",
}


def main() -> None:
    CONFIG.make_directories()
    historical = load_precipitation(CONFIG.historical_file)
    era5 = load_precipitation(CONFIG.era5_point_file)
    future = load_precipitation(CONFIG.future_file)
    corrected_future = load_precipitation(CONFIG.corrected_future_file)
    corrected_validation = load_precipitation(CONFIG.validation_file)

    historical_y = complete_annual_totals(historical)
    era5_y = complete_annual_totals(era5)
    future_y = complete_annual_totals(future)
    corrected_y = complete_annual_totals(corrected_future)

    fig = plt.figure(figsize=(16, 14))
    grid = gridspec.GridSpec(3, 2, figure=fig, hspace=0.42, wspace=0.3)

    axis = fig.add_subplot(grid[0, :])
    axis.plot(historical_y.index, historical_y, color=COLORS["historical"], marker="o", ms=3, label="CMIP6 historical")
    axis.plot(era5_y.index, era5_y, color=COLORS["era5"], marker="o", ms=3, label="ERA5 referans")
    axis.axhline(historical_y.mean(), color=COLORS["historical"], ls="--", alpha=0.6, label=f"CMIP6 ort.: {historical_y.mean():.0f} mm/yıl")
    axis.axhline(era5_y.mean(), color=COLORS["era5"], ls="--", alpha=0.6, label=f"ERA5 ort.: {era5_y.mean():.0f} mm/yıl")
    axis.set(title="Baz dönem: CMIP6 ve ERA5 (1980–2014)", xlabel="Yıl", ylabel="Yıllık yağış (mm)")
    axis.legend(ncol=2, fontsize=9)
    axis.grid(alpha=0.25)

    axis = fig.add_subplot(grid[1, :])
    axis.plot(future_y.index, future_y, color=COLORS["future"], marker="o", ms=3, label="SSP245 ham")
    axis.plot(corrected_y.index, corrected_y, color=COLORS["corrected"], marker="o", ms=3, label="SSP245 aylık QDM")
    axis.axhline(era5_y.mean(), color=COLORS["era5"], ls=":", label=f"ERA5 1980–2014 ort.: {era5_y.mean():.0f} mm/yıl")
    axis.set(title="Projeksiyon dönemi (2015–2049)", xlabel="Yıl", ylabel="Yıllık yağış (mm)")
    axis.legend(ncol=3, fontsize=9)
    axis.grid(alpha=0.25)

    axis = fig.add_subplot(grid[2, 0])
    x = np.arange(1, 13)
    for data, color, label in (
        (era5, COLORS["era5"], "ERA5 1980–2014"),
        (historical, COLORS["historical"], "CMIP6 1980–2014"),
        (future, COLORS["future"], "SSP245 ham 2015–2049"),
        (corrected_future, COLORS["corrected"], "SSP245 QDM 2015–2049"),
    ):
        axis.plot(x, monthly_climatology(data).values, marker="o", ms=4, color=color, label=label)
    axis.set_xticks(x, MONTH_LABELS)
    axis.set(title="Aylık klimatoloji", ylabel="Yağış (mm/ay)")
    axis.legend(fontsize=8)
    axis.grid(alpha=0.25)

    axis = fig.add_subplot(grid[2, 1])
    probabilities = np.linspace(0.01, 0.99, 99)
    raw_validation = historical.sel(time=slice(CONFIG.validation_start, CONFIG.historical_end))
    observed_validation = era5.sel(time=slice(CONFIG.validation_start, CONFIG.historical_end))
    obs_q = np.quantile(observed_validation.values, probabilities)
    raw_q = np.quantile(raw_validation.values, probabilities)
    corrected_q = np.quantile(corrected_validation.values, probabilities)
    maximum = 1.05 * max(obs_q.max(), raw_q.max(), corrected_q.max())
    axis.scatter(obs_q, raw_q, color=COLORS["historical"], s=18, alpha=0.7, label="Ham")
    axis.scatter(obs_q, corrected_q, color=COLORS["corrected"], s=18, alpha=0.7, label="QDM")
    axis.plot([0, maximum], [0, maximum], "k--", lw=1, label="1:1")
    axis.set(xlim=(0, maximum), ylim=(0, maximum), title="Bağımsız doğrulama Q-Q (2005–2014)", xlabel="ERA5 kantili (mm/ay)", ylabel="CMIP6 kantili (mm/ay)")
    axis.legend(fontsize=9)
    axis.grid(alpha=0.25)

    fig.suptitle(
        "Kayseri Yağış — MPI-ESM1-2-LR SSP245 Aylık Quantile Delta Mapping",
        fontsize=14,
        fontweight="bold",
        y=0.995,
    )
    path = CONFIG.figure_dir / "bias_correction_sonuclari.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Grafik kaydedildi: {path}")
    print("Sıradaki adım: 07_trend_analizi.py")


if __name__ == "__main__":
    main()
