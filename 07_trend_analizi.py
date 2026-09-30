"""Düzeltilmiş SSP245 serisinin yıllık ve mevsimsel trendlerini hesapla."""

from __future__ import annotations

import os

from climate_pipeline.config import CONFIG

os.environ.setdefault("MPLCONFIGDIR", str(CONFIG.project_root / ".cache" / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import pandas as pd

from climate_pipeline.io import complete_annual_totals, load_precipitation
from climate_pipeline.trends import calculate_trend, theil_sen_line, trend_suite


def trend_label(p_fdr: float, slope: float) -> str:
    if p_fdr >= 0.05:
        return "anlamlı değil"
    return "artan" if slope > 0 else "azalan"


def main() -> None:
    CONFIG.make_directories()
    raw = load_precipitation(CONFIG.future_file)
    corrected = load_precipitation(CONFIG.corrected_future_file)
    era5 = load_precipitation(CONFIG.era5_point_file)

    results, series_by_period = trend_suite(corrected)
    raw_annual = complete_annual_totals(raw)
    raw_result = calculate_trend(raw_annual)

    rows = {
        "Yıllık (ham)": raw_result.as_dict(),
        **{name: result.as_dict() for name, result in results.items()},
    }
    table = pd.DataFrame.from_dict(rows, orient="index")
    table.index.name = "Dönem"
    csv_path = CONFIG.result_dir / "trend_sonuclari.csv"
    table.to_csv(csv_path, float_format="%.8f")

    print("=" * 100)
    print("MANN–KENDALL VE THEIL–SEN TREND SONUÇLARI (SSP245, 2015–2049)")
    print("Mevsimsel/yıllık düzeltilmiş testlerde Benjamini–Hochberg FDR uygulanmıştır.")
    print("=" * 100)
    for name, result in [("Yıllık (ham)", raw_result), *results.items()]:
        print(
            f"{name:<20} tau={result.tau:+.3f}  p={result.p_value:.4f}  "
            f"p_FDR={result.p_fdr:.4f}  Sen={result.sen_slope:+.2f} "
            f"[{result.sen_low:+.2f}, {result.sen_high:+.2f}] mm/yıl  "
            f"{trend_label(result.p_fdr, result.sen_slope)}"
        )

    figure = plt.figure(figsize=(16, 12))
    grid = gridspec.GridSpec(3, 2, figure=figure, hspace=0.43, wspace=0.3)
    color_corrected = "#388E3C"
    color_raw = "#F57C00"
    color_trend = "#C2185B"
    color_reference = "#1976D2"

    axis = figure.add_subplot(grid[0, :])
    annual = series_by_period["Yıllık"]
    annual_result = results["Yıllık"]
    axis.bar(annual.index, annual.values, color=color_corrected, alpha=0.72, label="QDM yıllık toplam")
    axis.plot(raw_annual.index, raw_annual.values, color=color_raw, marker="o", ms=3, alpha=0.75, label="Ham yıllık toplam")
    axis.plot(annual.index, theil_sen_line(annual, annual_result), color=color_trend, lw=2.2, ls="--", label=f"Theil–Sen: {annual_result.sen_slope:+.2f} mm/yıl")
    era5_mean = complete_annual_totals(era5).mean()
    axis.axhline(era5_mean, color=color_reference, ls=":", lw=1.7, label=f"ERA5 1980–2014 ort.: {era5_mean:.0f} mm/yıl")
    axis.set(
        title=f"Yıllık trend | tau={annual_result.tau:+.3f}, p_FDR={annual_result.p_fdr:.3f} ({trend_label(annual_result.p_fdr, annual_result.sen_slope)})",
        xlabel="Yıl",
        ylabel="Yağış (mm)",
    )
    axis.legend(ncol=2, fontsize=9)
    axis.grid(alpha=0.25)

    positions = {
        "Kış (DJF)": grid[1, 0],
        "İlkbahar (MAM)": grid[1, 1],
        "Yaz (JJA)": grid[2, 0],
        "Sonbahar (SON)": grid[2, 1],
    }
    for name, position in positions.items():
        series = series_by_period[name]
        result = results[name]
        axis = figure.add_subplot(position)
        axis.bar(series.index, series.values, color=color_corrected, alpha=0.68)
        axis.plot(series.index, theil_sen_line(series, result), color=color_trend, lw=2, ls="--", label=f"Theil–Sen: {result.sen_slope:+.2f} mm/yıl")
        axis.axhline(series.mean(), color="gray", lw=1, ls=":", label=f"Ort.: {series.mean():.0f} mm")
        axis.set(title=f"{name} | tau={result.tau:+.3f}, p_FDR={result.p_fdr:.3f}", xlabel="Mevsim yılı", ylabel="Yağış (mm)")
        axis.legend(fontsize=8)
        axis.grid(alpha=0.25)

    figure.suptitle(
        "Kayseri Yağış Trend Analizi — SSP245 Aylık QDM (2015–2049)",
        fontsize=14,
        fontweight="bold",
    )
    figure_path = CONFIG.figure_dir / "trend_analizi.png"
    figure.savefig(figure_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    print(f"\nCSV: {csv_path}\nGrafik: {figure_path}")


if __name__ == "__main__":
    main()
