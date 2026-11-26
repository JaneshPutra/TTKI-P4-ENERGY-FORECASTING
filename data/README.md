# Data — provenance dan lisensi

**Sumber:** UCI *Individual Household Electric Power Consumption* (Hébrail & Bérard, 2012), DOI 10.24432/C58K54.
Salinan Kaggle: `uciml/electric-power-consumption-data-set` (lisensi: Open Database License / Database Contents License).

- 2.075.259 baris per menit, 16 Des 2006 – 26 Nov 2010, satu rumah tangga di Sceaux (Prancis).
- Variabel target: `Global_active_power` (kW, rerata per menit). Energi harian (kWh) = Σ(kW/60) per hari.
- Data hilang pada berkas asli ditandai `?` (±1,25% baris).

## Berkas di folder ini

| Berkas | Isi |
|---|---|
| `daily_energy_from_kaggle.csv` | Agregasi harian (1.442 hari): `date, energy_kwh_raw, valid_minutes, missing_minutes, complete, energy_kwh`. Ini turunan (bukan data mentah) dan **diambil dari repositori tim**; lihat catatan verifikasi di bawah. |
| `raw/` (tidak di-commit) | Letakkan `household_power_consumption.txt` hasil unduhan Kaggle/UCI di sini. |

## Verifikasi agregasi harian (WAJIB dilakukan sekali)

Pada saat eksperimen dijalankan, lingkungan kerja tidak dapat mengakses Kaggle/UCI, sehingga agregasi harian
**tidak dihitung ulang dari data menit**. Berkas harian divalidasi integritasnya (tanggal kontigu, `valid_minutes + missing_minutes = 1440`,
penskalaan ulang konsisten) tetapi bukan diturunkan dari data mentah oleh pipeline ini. Untuk memverifikasinya:

```bash
python src/make_daily.py data/raw/household_power_consumption.txt \
    --out data/daily_energy_regen.csv --compare
```

Selisih maksimum seharusnya ≈ 0. Bila ada perbedaan, gunakan berkas hasil `make_daily.py` lalu jalankan ulang seluruh pipeline.
