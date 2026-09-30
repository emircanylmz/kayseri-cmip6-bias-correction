# Kayseri CMIP6 Yağış Bias Correction

Bu proje, MPI-ESM1-2-LR modelinin aylık yağış verisini Kayseri için ERA5 yeniden
analiziyle değerlendirir, SSP2-4.5 projeksiyonuna aylık **Quantile Delta Mapping
(QDM)** uygular ve yıllık/mevsimsel trendleri hesaplar.

> ERA5 doğrudan istasyon gözlemi değil, yeniden analiz referansıdır. Tek model ve
> tek senaryo sonucu deterministik bir gelecek tahmini olarak yorumlanmamalıdır.

## Bilimsel tasarım

- Hedef koordinat: **38.73°K, 35.48°D**.
- CMIP6 ve ERA5 aynı hedef koordinata bilinear enterpole edilir.
- Birimler kaynak metadata'sı kontrol edilerek `mm/ay` biçimine dönüştürülür.
- Kalibrasyon: **1980–2004**.
- Bağımsız doğrulama: **2005–2014**.
- Nihai SSP245 düzeltmesi: **1980–2014** baz dönemiyle yeniden eğitilir.
- Her takvim ayı ayrı düzeltilir.
- Multiplicative QDM göreli iklim değişikliği sinyalini kantil bazında korur;
  historical maksimumu aşan gelecek değerleri gözlem maksimumunda kırpmaz.
- Trendler Mann–Kendall tau/p ve Theil–Sen eğimi ile raporlanır.
- Beş düzeltilmiş trend testi için Benjamini–Hochberg FDR düzeltmesi yapılır.
- DJF'de Aralık bir sonraki mevsim yılına atanır ve eksik kışlar dışlanır.

## Kurulum

Test edilen ortam Python 3.12.4'tür.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

CDS hesabı oluşturun, güncel kimlik bilgilerini `~/.cdsapirc` içine ekleyin ve
aşağıdaki iki veri kümesinin kullanım koşullarını CDS web sayfasında kabul edin:

- `projections-cmip6`
- `reanalysis-era5-single-levels-monthly-means`

Kimlik bilgilerini kesinlikle proje içine veya Git'e eklemeyin.

## Çalıştırma

Tüm hattı tek komutla çalıştırmak için:

```bash
python run_pipeline.py
```

İndirilmiş ham veri mevcutsa belirli bir adımdan devam edilebilir:

```bash
python run_pipeline.py --from-step 3
```

Mevcut indirmeleri yenilemek için:

```bash
python run_pipeline.py --force-download
```

Adımlar ayrı ayrı da çalıştırılabilir:

1. `01_veri_indir.py`: Güncel CDS API sözleşmesiyle bölgesel verileri indirir.
2. `02_zip_ac.py`: CMIP6 ZIP'lerini güvenli açar ve `manifest.json` üretir.
3. `03_veri_kontrol.py`: Koordinat, zaman, birim, NaN ve negatif değerleri kontrol eder.
4. `04_quantile_mapping.py`: Aylık QDM ve bağımsız doğrulama serisini üretir.
5. `05_dogrulama_metrikleri.py`: Dağılım/klimatoloji doğrulamasını raporlar.
6. `06_gorsellestirme.py`: Dört panelli sonuç grafiğini üretir.
7. `07_trend_analizi.py`: Düzeltilmiş yıllık ve mevsimsel trendleri hesaplar.

## Çıktılar

```text
data/
├── raw/                         # CDS indirmeleri ve manifest
└── processed/
    ├── cmip6_historical_kayseri.nc
    ├── cmip6_ssp245_kayseri.nc
    ├── era5_kayseri.nc
    ├── validation_qdm_kayseri.nc
    └── cmip6_ssp245_qdm_kayseri.nc

sonuclar/
├── qdm_metadata.json
├── validation_metrics.csv
└── trend_sonuclari.csv

gorseller/
├── dogrulama_tablosu.png
├── bias_correction_sonuclari.png
└── trend_analizi.png
```

NetCDF çıktıları tarih, birim, hedef koordinat, yöntem ve kaynak bilgisini korur.

## Testler

```bash
python -m pytest
```

Testler QDM'nin değişim sinyalini korumasını, uç değerleri kırpmamasını, sıfır ve
tekrarlanan değerleri işlemesini, birim dönüşümünü, eksik ay kontrolünü, güvenli
ZIP açmayı, DJF yıl atamasını, Theil–Sen çizgisini ve doğrulama metriklerini kapsar.

## Doğrulanmış örnek sonuç

30 Eylül 2026 tarihinde canlı CDS verisiyle yapılan uçtan uca çalıştırmada
bağımsız 2005–2014 doğrulama dönemi için aşağıdaki iyileşmeler elde edilmiştir:

| Metrik | CMIP6 ham | CMIP6 QDM |
|---|---:|---:|
| PBIAS | %25.50 | %6.10 |
| Aylık klimatoloji RMSE | 32.50 mm/ay | 11.31 mm/ay |
| Wasserstein uzaklığı | 16.62 mm/ay | 6.80 mm/ay |
| Q95 farkı | 68.16 mm/ay | 25.63 mm/ay |

Düzeltilmiş SSP245 yıllık trendi `+0.41 mm/yıl` olarak hesaplanmış, ancak
FDR-düzeltilmiş `p=0.921` olduğundan istatistiksel olarak anlamlı bulunmamıştır.

## Yorumlama sınırları

- Aylık bias correction günlük şiddet/sıklık istatistiklerini düzeltmez.
- Yerel orografik yağış için istasyon verisi varsa ERA5'e tercih edilebilir veya
  ek doğrulama kaynağı olarak kullanılmalıdır.
- Sağlam belirsizlik analizi için birden fazla CMIP6 modeli, üyesi ve emisyon
  senaryosu aynı yöntemle değerlendirilmelidir.
- Trend anlamlılığı fiziksel nedensellik veya kesin gelecek tahmini anlamına gelmez.
