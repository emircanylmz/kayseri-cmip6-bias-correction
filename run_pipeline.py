"""Run the complete Kayseri climate-analysis pipeline with one command."""

from __future__ import annotations

import argparse
import subprocess
import sys

from climate_pipeline.config import CONFIG


STEPS = [
    "01_veri_indir.py",
    "02_zip_ac.py",
    "03_veri_kontrol.py",
    "04_quantile_mapping.py",
    "05_dogrulama_metrikleri.py",
    "06_gorsellestirme.py",
    "07_trend_analizi.py",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-step", type=int, default=1, choices=range(1, 8))
    parser.add_argument("--to-step", type=int, default=7, choices=range(1, 8))
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()
    if args.from_step > args.to_step:
        parser.error("--from-step, --to-step değerinden büyük olamaz")

    for number, script in enumerate(STEPS, start=1):
        if not args.from_step <= number <= args.to_step:
            continue
        command = [sys.executable, str(CONFIG.project_root / script)]
        if number == 1 and args.force_download:
            command.append("--force")
        print(f"\n[{number}/7] {script}", flush=True)
        subprocess.run(command, cwd=CONFIG.project_root, check=True)
    print("\nBütün seçili adımlar başarıyla tamamlandı.")


if __name__ == "__main__":
    main()
