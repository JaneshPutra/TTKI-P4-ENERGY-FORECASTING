# Peramalan Energi Listrik Harian Satu Rumah Tangga — Topik P4 (TTKI)

Evaluasi fitur lag dan rata-rata bergulir pada peramalan energi listrik harian satu rumah tangga, dengan validasi kronologis (walk-forward),
pembanding K-fold teracak, dan perbandingan kebijakan data hilang. Paper: `paper/TTKI_KelompokXX_TopikP4.docx` (PDF: `.pdf`).

> Placeholder yang harus diisi kelompok: nama penulis, nomor kelompok, tag rilis GitHub, konfirmasi pada Pernyataan Penggunaan AI.

## Pertanyaan penelitian dan hipotesis

- **RQ1** Seberapa besar fitur lag (t−1, t−7) dan rata-rata bergulir (7, 14 hari) menurunkan MAE dibanding baseline naïve/seasonal naïve dan model kalender saja? (H1: menurunkan)
- **RQ2** Seberapa optimistis K-fold teracak dibanding walk-forward pada hari uji yang identik? (H2: lebih optimistis)
- **RQ3** Apakah kesimpulan bergantung pada kebijakan data hilang P1–P4? (H3: zero-fill memperburuk MAE)

Seluruh keputusan metodologis dibekukan sebelum data uji dijalankan: `docs/decisions.md` (termasuk change log).

## Data

UCI *Individual Household Electric Power Consumption* (DOI 10.24432/C58K54; salinan Kaggle `uciml/electric-power-consumption-data-set`).
Lihat `data/README.md` untuk provenance, lisensi, dan **verifikasi agregasi harian dari data menit** (`src/make_daily.py --compare`).
`data/daily_energy_from_kaggle.csv` adalah turunan harian (1.442 hari) dari repositori tim; data mentah tidak ikut di-commit.

## Struktur

```
data/          agregasi harian + README provenance
src/           common.py (fitur, model, walk-forward), check_leakage.py, run_validation.py, run_test.py,
               run_random_cv.py, analyze.py, stats_utils.py, make_figures.py, make_daily.py
results/       semua CSV/JSON hasil (metrics_primary.csv, contrasts_primary.csv, optimism_randomcv.csv, policy_*.csv, ...)
figures/       fig1–fig6 (PNG)
paper/         build_paper.py (menyusun DOCX dari results/), DOCX, PDF
references/    literature_matrix.csv (16 sumber)
docs/          decisions.md, proposal_2halaman.md, template response-to-review dan kontribusi/kejujuran
```

## Lingkungan

Python 3.13; versi paket di `requirements.txt` dan `environment-freeze.txt` (pandas 3.0.5, numpy 2.5.3, scikit-learn 1.9.1, scipy 1.18.1, matplotlib 3.11.2, python-docx 1.2.0).
Seed global 42; bootstrap seed 7; K-fold seed 100–109.

```bash
pip install -r requirements.txt
```

## Urutan menjalankan (dari root repo)

```bash
python src/check_leakage.py     # uji kebocoran + integritas input -> results/leakage_check.txt
python src/run_validation.py    # tuning pada validation 2009 -> selected_hyperparams.json (dikunci)
python src/run_test.py          # evaluasi test 2010, dijalankan SEKALI setelah hyperparameter dikunci
python src/run_random_cv.py     # pembanding K-fold teracak (RQ2)
python src/analyze.py           # metrik, bootstrap, DM + Holm, sensitivitas kebijakan
python src/make_figures.py      # figures/
python paper/build_paper.py     # paper/TTKI_KelompokXX_TopikP4.docx (PDF: soffice --headless --convert-to pdf)
```

## Desain singkat

- Target: energi harian (kWh); split kronologis train 2006-12-16..2008-12-31, validation 2009, test 2010-01-01..2010-11-26.
- Walk-forward expanding window, refit tiap 7 hari, prediksi satu hari ke depan dengan riwayat aktual; fitur hanya dari data ≤ t−1.
- Baseline: naïve (t−1), seasonal naïve (t−7). Skenario: A kalender; B = A + lag1, lag7; C = B + roll7, roll14; R = A + roll7, roll14 (ablasi).
- Model: Ridge dan HistGradientBoostingRegressor. Metrik utama MAE; juga RMSE dan MASE.
- Inferensi: moving-block bootstrap (blok 7, B=10.000), uji Diebold–Mariano (koreksi HLN, Newey–West), koreksi Holm.

## Ringkasan hasil (test 2010, 258 hari evaluasi; MAE kWh/hari)

| Model | A (kalender) | B (+lag) | C (+lag+rolling) | R (rolling saja) |
|---|---|---|---|---|
| Ridge | 4,77 | 4,51 | 4,40 | 4,53 |
| HGB | 4,75 | 4,24 | 4,23 | 4,38 |

Baseline: naïve 5,23; seasonal naïve 6,10. Semua model lebih baik dari seasonal naïve (6 dari 8 konfigurasi tetap signifikan setelah Holm).
Keunggulan fitur historis atas model kalender (5–11%) searah dengan H1, tetapi **tidak signifikan setelah koreksi Holm**.
K-fold teracak tidak terbukti lebih optimistis secara konsisten (H2 tidak didukung). Pengaruh kebijakan data hilang kecil; bukti H3 hanya bersifat arah.
Angka lengkap dan interval kepercayaan: `results/*.csv`.

## Keterbatasan

- Satu rumah tangga; hasil tidak dapat digeneralisasi ke rumah tangga lain.
- Agregasi harian berasal dari repositori tim dan belum dihitung ulang dari data menit oleh pipeline ini (lihat `data/README.md`).
- Sampel uji kecil (258 hari) sehingga interval kepercayaan lebar; sebagian analisis RQ3 (himpunan evaluasi E1/E2/E3) ditetapkan setelah melihat hasil uji dan dicatat sebagai analisis pasca-uji di `docs/decisions.md`.
- Kebijakan P2 (hanya hari lengkap) dan P4 (zero-fill) bersifat pembanding; target penilaian selalu observasi P1.
- Matriks literatur diverifikasi pada tingkat metadata/abstrak; kolom "lokasi bukti" harus diisi penulis setelah membaca teks penuh.

## Penggunaan AI

Asisten AI (Claude) digunakan untuk merancang protokol, menulis kode, dan menyusun draf paper atas permintaan mahasiswa. Penulis bertanggung jawab memverifikasi seluruh isi,
menjalankan ulang pipeline, dan melengkapi pernyataan AI pada paper. Tidak ada kredensial di repositori (`.gitignore` mengecualikan `kaggle.json`, `.env`, dan `data/raw/`).
