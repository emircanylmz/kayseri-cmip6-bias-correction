"""Bağımsız 2005–2014 dönemi için dağılım ve klimatoloji metriklerini hesapla."""

from __future__ import annotations

import os

from climate_pipeline.config import CONFIG

os.environ.setdefault("MPLCONFIGDIR", str(CONFIG.project_root / ".cache" / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from climate_pipeline.io import load_precipitation
from climate_pipeline.validation import metrics_table


def main() -> None:
    CONFIG.make_directories()
    historical = load_precipitation(CONFIG.historical_file)
    era5 = load_precipitation(CONFIG.era5_point_file)
    corrected = load_precipitation(CONFIG.validation_file)
    raw_validation = historical.sel(
        time=slice(CONFIG.validation_start, CONFIG.historical_end)
    )
    observed_validation = era5.sel(
        time=slice(CONFIG.validation_start, CONFIG.historical_end)
    )

    table = metrics_table(raw_validation, corrected, observed_validation)
    csv_path = CONFIG.result_dir / "validation_metrics.csv"
    table.to_csv(csv_path, float_format="%.6f")

    print("=" * 88)
    print("BAĞIMSIZ DOĞRULAMA (Kalibrasyon: 1980–2004, doğrulama: 2005–2014)")
    print("=" * 88)
    print(table.round(3).to_string())

    formatted = []
    for _, row in table.iterrows():
        formatted.append([f"{value:.2f}" for value in row])

    fig, axis = plt.subplots(figsize=(12, 5.8))
    axis.axis("off")
    visual = axis.table(
        cellText=formatted,
        rowLabels=table.index,
        colLabels=table.columns,
        cellLoc="center",
        loc="center",
    )
    visual.auto_set_font_size(False)
    visual.set_fontsize(9.5)
    visual.scale(1.05, 1.7)
    for column in range(len(table.columns)):
        visual[0, column].set_facecolor("#1F4E79")
        visual[0, column].set_text_props(color="white", fontweight="bold")
    axis.set_title(
        "Kayseri Aylık Yağış — Bağımsız Bias-Correction Doğrulaması\n"
        "Kalibrasyon 1980–2004 | Doğrulama 2005–2014",
        fontsize=12,
        fontweight="bold",
        pad=22,
    )
    figure_path = CONFIG.figure_dir / "dogrulama_tablosu.png"
    fig.savefig(figure_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"\nCSV: {csv_path}\nGrafik: {figure_path}")
    print("Sıradaki adım: 06_gorsellestirme.py")


if __name__ == "__main__":
    main()
