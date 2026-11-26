# Proposal Singkat — P4 (Lampiran A Buku Petunjuk)

| Komponen | Isian |
|---|---|
| Kode & judul paper | P4 — *Evaluating Lag-Based Feature Engineering for Short-Term Household Electricity Consumption Forecasting* (judul paper: Evaluasi Fitur Lag dan Rata-rata Bergulir pada Peramalan Energi Listrik Harian Satu Rumah Tangga: Validasi Kronologis, Optimisme Validasi Acak, dan Kebijakan Data Hilang) |
| Rumusan masalah | Peramalan konsumsi listrik satu rumah tangga sering dievaluasi tanpa pembanding musiman yang tepat, dengan pembagian data yang tidak dijelaskan, dan dengan penanganan data hilang yang tidak dilaporkan. Belum jelas seberapa besar fitur historis sederhana memperbaiki galat bila dievaluasi secara kronologis, apakah validasi acak melebih-lebihkan manfaatnya, dan apakah kesimpulan bergantung pada kebijakan data hilang. |
| Literatur pendukung | Hewamalage et al. (2023) doi:10.1007/s10618-022-00894-5; Cerqueira et al. (2020) doi:10.1007/s10994-020-05910-7; Bergmeir et al. (2018) doi:10.1016/j.csda.2017.11.003; Hussain et al. (2025) doi:10.3390/electronics14071383; Kim & Cho (2019) doi:10.1016/j.energy.2019.05.230. Matriks lengkap (16 sumber): `references/literature_matrix.csv` |
| Research gap | Kandidat gap (perlu verifikasi penelusuran lebih luas): belum ditemukan evaluasi yang memisahkan kontribusi lag dan rata-rata bergulir terhadap baseline seasonal naïve pada satu rumah tangga dengan validasi kronologis, membandingkannya dengan K-fold teracak pada hari uji identik, dan membandingkan kebijakan data hilang secara eksplisit |
| Research question | RQ1 (manfaat fitur lag/rolling vs baseline dan kalender); RQ2 (optimisme K-fold teracak pada hari uji identik); RQ3 (ketahanan kesimpulan terhadap kebijakan data hilang) |
| Hipotesis | H1 fitur historis menurunkan MAE vs kalender; H2 K-fold teracak lebih optimistis; H3 zero-fill memperburuk MAE |
| Dataset | Kaggle `uciml/electric-power-consumption-data-set`; 2.075.259 baris per menit; target Global_active_power (kW) diagregasi menjadi kWh/hari; lisensi: Open Database License / Database Contents License |
| Baseline | Naïve (kemarin) dan seasonal naïve (7 hari lalu): pembanding standar peramalan harian berpola mingguan |
| Skenario eksperimen | A kalender; B +lag 1 dan 7; C +rolling 7 dan 14; R ablasi (rolling tanpa lag); empat kebijakan data hilang P1–P4 |
| Metrik & split | MAE (utama), RMSE, MASE; train 2006–2008, validation 2009, test 2010; walk-forward refit tiap 7 hari |
| Risiko & mitigasi | Kebocoran: fitur dari deret digeser, diuji otomatis; data hilang: empat kebijakan dibandingkan; ketidakstasioneran: walk-forward + analisis residual; overclaim: interval bootstrap dan koreksi Holm; kesesuaian data: agregasi harian diverifikasi ulang dari data menit dengan `src/make_daily.py ... --compare` |
| Reproducibility | Repositori GitHub kelompok; README, `requirements.txt`, `environment-freeze.txt`, seed tercatat, `docs/decisions.md` |
