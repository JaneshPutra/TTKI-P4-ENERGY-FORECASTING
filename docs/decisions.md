# Catatan Keputusan Metodologi — P4 (Peramalan Energi Listrik Harian Rumah Tangga)

- **Dibuat:** 2026-11-25
- **Status:** DIBEKUKAN sebelum `src/run_test.py` dan `src/run_random_cv.py` dijalankan.
- **Aturan:** semua keputusan di bawah ditetapkan **sebelum** data uji (2010) dievaluasi. Perubahan sesudahnya hanya boleh
  untuk memperbaiki kesalahan teknis (bug), dicatat di bagian Log perubahan, dan tidak boleh dipilih berdasarkan hasil uji.

## 1. Pertanyaan penelitian dan hipotesis

| Kode | Pernyataan |
|---|---|
| RQ1 | Seberapa besar fitur lag (1 dan 7 hari) dan rata-rata bergulir (7 dan 14 hari) menurunkan galat peramalan energi harian dibandingkan baseline *naive*, *seasonal naive*, dan fitur kalender saja, pada validasi kronologis? |
| RQ2 | Seberapa besar validasi acak (K-fold teracak) memberi estimasi galat yang lebih optimistis daripada walk-forward pada **himpunan hari uji yang sama**? |
| RQ3 | Apakah kesimpulan RQ1 tahan terhadap kebijakan penanganan data hilang (empat kebijakan, bagian 4)? |
| H1 | Fitur historis menurunkan MAE terhadap kalender saja. |
| H2 | K-fold teracak menghasilkan MAE lebih rendah (lebih optimistis) daripada walk-forward pada hari yang sama. |
| H3 | Mengisi hari hilang dengan nol (tanpa penskalaan) memperburuk MAE dibanding kebijakan yang menghormati data hilang. |

## 2. Sumber data dan kontrol asal-usul

| Item | Isian |
|---|---|
| Dataset | Individual Household Electric Power Consumption (Hébrail & Bérard), UCI, DOI 10.24432/C58K54 |
| Salinan wajib | Kaggle `uciml/electric-power-consumption-data-set` (diunduh tim pada 12 November 2026 menurut catatan repositori tim) |
| Lisensi di Kaggle | Database: Open Database License; Contents: Database Contents License |
| Berkas masukan eksperimen | `data/daily_energy_from_kaggle.csv`: agregasi harian (jumlah daya/60 atas menit valid, jumlah menit valid) dari berkas Kaggle di atas |
| Catatan keterbatasan | Lingkungan tempat eksperimen dijalankan tidak dapat mengunduh Kaggle/UCI. Agregasi harian diambil dari keluaran skrip audit tim; `src/make_daily.py` menyediakan jalur regenerasi dari berkas menit mentah dan **harus dijalankan penulis** untuk memverifikasi kesamaan (`--compare`). |

Pemeriksaan integritas berkas harian (dijalankan di `src/check_leakage.py`, fungsi `check_input`): 1.442 hari berurutan tanpa celah;
`valid_minutes + missing_minutes = 1440` pada semua hari; nilai terskala = `energy_kwh_raw × 1440 / valid_minutes`.

## 3. Target dan unit observasi

- Unit observasi: **hari**. Target: energi aktif harian (kWh) = Σ(`Global_active_power`/60) atas menit valid.
- Horizon: **satu hari ke depan** (prediksi hari *t* memakai informasi sampai hari *t*−1 saja).

## 4. Empat kebijakan data hilang (faktor eksperimen RQ3)

| Kode | Deret fitur/latih | Aturan |
|---|---|---|
| **P1 (utama)** | `rescale10` | hari dengan ≤10% menit hilang diskalakan ke 1.440 menit; >10% menjadi NaN dan dibuang dari pelatihan/evaluasi; fitur yang jendelanya memuat NaN dibuang |
| P2 | `complete` | hanya hari dengan 1.440 menit valid; lainnya NaN dan dibuang |
| P3 | `rescale10 + imputasi kausal` | seperti P1, tetapi NaN pada **deret fitur** diisi nilai hari yang sama pada minggu-minggu sebelumnya (t−7, t−14, t−21; bila semuanya kosong, nilai valid terakhir). Target NaN tidak pernah diimputasi dan tidak dinilai |
| P4 | `zero-fill` | jumlah mentah menit valid tanpa penskalaan, menit hilang dianggap nol (praktik umum pada notebook publik) |

Aturan skor: **target yang dinilai selalu target P1 yang teramati** (hari ≤10% hilang, terskala), apa pun kebijakannya.
Perbandingan antarkebijakan dilaporkan pada **himpunan hari bersama** (hari dengan target lengkap dan fitur lengkap pada P2,
yang merupakan himpunan terkecil sehingga merupakan himpunan bagian dari yang lain). Hasil pada himpunan sendiri tiap kebijakan dilaporkan sebagai tambahan.

## 5. Pembagian kronologis (tiga tingkat, Buku Petunjuk §5.3)

| Bagian | Periode | Fungsi |
|---|---|---|
| Train | 16 Des 2006 – 31 Des 2008 | fitting awal |
| Validation | 1 Jan – 31 Des 2009 | memilih hyperparameter (protokol walk-forward yang sama dengan uji) |
| Test | 1 Jan – 26 Nov 2010 | dilaporkan **sekali** setelah semua keputusan dibekukan |

Tidak ada pengacakan pada evaluasi utama.

## 6. Skenario fitur (perubahan terkontrol, model sama)

| Kode | Fitur |
|---|---|
| A | kalender: hari dalam minggu (one-hot, 7) + bulan (one-hot, 12) |
| B | A + `lag1` + `lag7` |
| C | B + `roll7` + `roll14` (rata-rata bergulir dari deret yang digeser 1 hari) |
| R (ablasi) | A + `roll7` + `roll14` tanpa lag, untuk memisahkan kontribusi lag dan rata-rata bergulir |

Pencegahan kebocoran: `lag_k = y.shift(k)`; `roll_w = y.shift(1).rolling(w).mean()` (jendela harus penuh, `min_periods=w`).
Diuji otomatis di `src/check_leakage.py` (perturbasi masa depan tidak boleh mengubah fitur hari *t*).

## 7. Model dan tuning

| Model | Konfigurasi |
|---|---|
| Ridge | `StandardScaler` + `Ridge`; scaler di-*fit* hanya pada data latih tiap *refit*. Grid α ∈ {1; 10; 30; 100; 300; 1000; 3000} |
| Gradient boosting | `HistGradientBoostingRegressor`, `max_iter=150`, `early_stopping=False`; grid `learning_rate` ∈ {0,05; 0,1} × `max_depth` ∈ {1; 2; 3} × `min_samples_leaf` ∈ {10; 25} |

Hyperparameter dipilih per (model, skenario) dengan MAE terendah pada validation memakai walk-forward (expanding window,
*refit* tiap 7 hari, pada P1). Hasil terkunci di `results/selected_hyperparams.json` sebelum test dijalankan.
Hyperparameter yang sama dipakai untuk semua kebijakan data hilang (tidak di-tuning ulang per kebijakan).

## 8. Protokol evaluasi

1. **Walk-forward (utama):** expanding window dari awal data; model dilatih ulang tiap 7 hari dengan seluruh data sebelum origin; meramal 7 hari berikutnya satu-hari-ke-depan memakai riwayat aktual; hyperparameter tetap.
2. **K-fold teracak (pembanding RQ2):** 5-fold teracak × 10 pengulangan (seed 100–109) pada semua hari berfitur lengkap dari seluruh periode, hyperparameter tetap dari validation. Galat dihitung per hari (*out-of-fold*, dirata-ratakan antar pengulangan) lalu **dibatasi pada hari uji himpunan evaluasi E1**, sehingga hari yang dibandingkan identik dengan walk-forward.
3. **Metrik:** MAE (utama), RMSE, MASE (skala = MAE seasonal-naive dalam sampel pada train), penurunan relatif MAE.
4. **Inferensi:** selisih MAE berpasangan dengan *moving-block bootstrap* (panjang blok 7, 10.000 replikasi, seed 7) untuk interval kepercayaan 95%; uji Diebold–Mariano dengan koreksi Harvey–Leybourne–Newbold (loss = galat absolut, *Newey–West* bandwidth 7); koreksi Holm dalam satu keluarga kontras.

Kontras yang ditetapkan sebelumnya (keluarga uji): tiap skenario vs seasonal naive; B vs A, C vs A, C vs B, R vs A (per model); gradient boosting vs Ridge per skenario.

## 9. Ancaman validitas yang sudah diketahui

- Satu rumah tangga, satu periode uji → generalisasi terbatas.
- Hari uji yang dinilai lebih sedikit daripada 330 karena NaN dan jendela fitur yang kosong.
- Tidak ada variabel eksternal (cuaca, hari libur).
- Selisih kecil antarmodel bisa berada dalam variasi sampling; karena itu dilaporkan interval dan uji, bukan hanya angka titik.
- Sumber data harian tidak diagregasi ulang dari menit mentah di lingkungan ini (lihat bagian 2).

## 10. Log perubahan

| Tanggal | Perubahan | Alasan |
|---|---|---|
| 2026-11-25 | Dokumen dibuat dan dibekukan | Sebelum menjalankan evaluasi uji |
| 2026-11-25 | Grid diperluas: Ridge α dari {0,1…300} menjadi {1…3000}; HGB `max_depth` dari {2,4} menjadi {1,2,3} | Putaran pertama tuning di **validation** menghasilkan nilai optimum di tepi grid (α=300; kedalaman=2 sebagai nilai terkecil). Keputusan hanya memakai data validation; data uji belum pernah dievaluasi |
| 2026-11-25 | Ditambahkan (setelah `run_test.py` dan `run_random_cv.py`): (a) himpunan evaluasi RQ3 diperjelas menjadi E1 (258 hari; P1, P3, P4), E3 (314 hari; P3, P4) dan E2 (138 hari; semua kebijakan); (b) keluarga uji Holm untuk H3 = E3, P4 vs P3 (10 konfigurasi); kontras E1/E2 deskriptif; (c) konfigurasi untuk plot residual = terbaik pada validation di antara skenario A–C | (a) Pada E2 fitur identik antarkebijakan sehingga hanya efek data latih yang terukur; efek imputasi/zero-fill baru terlihat pada hari yang jendelanya menyentuh celah. (b) Banyak kontras E1/E2 identik secara konstruksi. (c) Aturan hanya memakai angka validation yang sudah final sebelum test. **Ini keputusan analisis pasca-uji; angka metrik dan model tidak diubah.** |
