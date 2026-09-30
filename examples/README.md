# Üretilmiş örnek çıktılar

Bu klasör, projenin 30 Eylül 2026 tarihinde canlı Copernicus Climate Data Store
verileriyle çalıştırılmasından alınmış örnekleri içerir.

Kullanılan veri:

- CMIP6 MPI-ESM1-2-LR, `r1i1p1f1`, historical 1980–2014
- CMIP6 MPI-ESM1-2-LR, `r1i1p1f1`, SSP2-4.5 2015–2049
- ERA5 aylık ortalama yeniden analiz, 1980–2014
- Hedef koordinat: 38.73°K, 35.48°D

Klasörler:

- `figures/`: doğrulama, bias correction ve trend grafikleri
- `results/`: doğrulama/trend CSV tabloları ve QDM metadata'sı
- `data/`: düzeltilmiş gelecek serisi ile bağımsız doğrulama serisinin NetCDF örnekleri

Ham CDS indirmeleri paylaşılmaz. Örnek dosyalarda API anahtarı, CDS kimlik
bilgisi veya yerel kullanıcı yolu bulunmaz. Sonuçlar tek model, tek ensemble üyesi
ve tek senaryoya aittir; deterministik gelecek tahmini olarak yorumlanmamalıdır.
