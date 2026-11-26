"""Membangun paper/TTKI_Kelompok_XX_TopikP4.docx dari results/*.csv (angka tidak diketik manual)."""
import json
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
R, FIG = ROOT / "results", ROOT / "figures"
OUT = ROOT / "paper" / "TTKI_KelompokXX_TopikP4.docx"

# ------------------------------------------------------------------ angka
met = pd.read_csv(R / "metrics_primary.csv")
con = pd.read_csv(R / "contrasts_primary.csv")
opt = pd.read_csv(R / "optimism_randomcv.csv")
pol = pd.read_csv(R / "policy_sensitivity.csv")
pc = pd.read_csv(R / "policy_contrasts.csv")
gain = pd.read_csv(R / "policy_gain_vs_A.csv")
vb = pd.read_csv(R / "validation_best.csv")
vbl = pd.read_csv(R / "validation_baselines.csv")
dow = pd.read_csv(R / "residual_by_dow.csv")
ds = pd.read_csv(R / "dataset_table.csv")
S = json.load(open(R / "summary.json"))


def f(x, d=3):
    out = f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return out.replace("-", "−")


def pct(x, d=1, sign=False):
    s = f(abs(x), d)
    if x < 0:
        return "−" + s + "%"
    return ("+" if sign else "") + s + "%"


def dn(x, d=1):
    return f(abs(x), d) + "%"


def pv(p):
    return "<0,001" if p < 0.001 else f(p, 3)


def M(m, s):
    return met[(met.model == m) & (met.scenario == s)].iloc[0]


def C(label):
    return con[con.contrast == label].iloc[0]


def O(m, s):
    return opt[(opt.model == m) & (opt.scenario == s)].iloc[0]


def P(sset, p, m, s):
    return pol[(pol["set"] == sset) & (pol.policy == p) & (pol.model == m) & (pol.scenario == s)].iloc[0]


def G(sset, p, m, s):
    return gain[(gain["set"] == sset) & (gain.policy == p) & (gain.model == m) & (gain.scenario == s)].iloc[0]


nv, sn = M("baseline", "naive"), M("baseline", "seasonal_naive")
best = M("HGB", "C")
rA, rB, rC, rR = (M("Ridge", s) for s in "ABCR")
gA, gB, gC, gR = (M("HGB", s) for s in "ABCR")
val = lambda m, s: vb[(vb.model == m) & (vb.scenario == s)].val_mae.iloc[0]
vsn = vbl[vbl.baseline == "seasonal_naive"].val_mae.iloc[0]
vnv = vbl[vbl.baseline == "naive"].val_mae.iloc[0]
e3 = pc[pc["set"] == "E3"].copy()
n_worse = int((e3.diff_kwh < 0).sum())
n_sig_raw = int((e3.p < 0.05).sum())
min_holm = e3.p_holm.min()
e3_rng = (e3.diff_kwh.abs().min(), e3.diff_kwh.abs().max())
e12 = pc[pc["set"].isin(["E1", "E2"]) & (pc.diff_kwh.abs() > 1e-9) & (pc.model != "baseline")]
max_e12 = e12.diff_kwh.abs().max(); n_e12 = len(e12); n_e12_nz = int(((e12.ci_lo > 0) | (e12.ci_hi < 0)).sum())
c_gain = gain[gain.scenario == "C"].gain_vs_A_pct
assert (c_gain < 0).all()
dow_lbl = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
we = dow[dow.dow >= 5].mae.mean()
wd = dow[dow.dow < 5].mae.mean()
ntest = S["n_test_eval_days"]
assert ntest == 258 and S["n_E3"] == 314 and S["n_E2"] == 138

# ------------------------------------------------------------- dokumen
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.2)
sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)
FONT = "Times New Roman"
st = doc.styles["Normal"]
st.font.name, st.font.size = FONT, Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(4)
st.paragraph_format.line_spacing = 1.05
for name, size, before, after in (("Heading 1", 12, 10, 4), ("Heading 2", 10.5, 6, 2)):
    h = doc.styles[name]
    h.font.name, h.font.size, h.font.bold, h.font.italic = FONT, Pt(size), True, name == "Heading 2"
    h.font.color.rgb = RGBColor(0, 0, 0)
    h.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    h.element.rPr.rFonts.set(qn("w:ascii"), FONT)
    h.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
    for att in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if h.element.rPr.rFonts.get(qn(att)) is not None:
            del h.element.rPr.rFonts.attrib[qn(att)]
    h.paragraph_format.space_before, h.paragraph_format.space_after = Pt(before), Pt(after)
    h.paragraph_format.keep_with_next = True


def para(text="", bold=False, italic=False, align=None, size=None, after=None, keep=False):
    p = doc.add_paragraph()
    add_runs(p, text, bold, italic, size)
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "j":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.keep_with_next = keep
    return p


def add_runs(p, text, bold=False, italic=False, size=None):
    """Mendukung *miring* sederhana: teks di antara tanda * dijadikan miring."""
    parts = text.split("*")
    for i, t in enumerate(parts):
        if not t:
            continue
        r = p.add_run(t)
        r.bold = bold
        r.italic = italic or (i % 2 == 1)
        if size:
            r.font.size = Pt(size)


def body(text):
    return para(text, align="j")


def h1(t):
    doc.add_heading(t, level=1)


def h2(t):
    doc.add_heading(t, level=2)


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def set_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge, sz in (("top", 8), ("bottom", 8), ("insideH", 2)):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), str(sz)); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "808080")
        b.append(e)
    tblPr.append(b)


def table(header, rows, widths_cm, size=8, align_first_left=True, caption=None, note=None, bold_rows=()):
    if caption:
        cp = para(caption, bold=False, size=9, after=2, keep=True)
        cp.runs[0].bold = True if cp.runs else None
    t = doc.add_table(rows=1, cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    set_borders(t)
    for j, wcm in enumerate(widths_cm):
        t.columns[j].width = Cm(wcm)
    for j, htxt in enumerate(header):
        c = t.rows[0].cells[j]
        c.width = Cm(widths_cm[j])
        shade(c, "E8EEF7")
        p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
        r = p.add_run(htxt); r.bold = True; r.font.size = Pt(size)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 and align_first_left else WD_ALIGN_PARAGRAPH.CENTER
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for j, v in enumerate(row):
            cells[j].width = Cm(widths_cm[j])
            p = cells[j].paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            r = p.add_run(str(v)); r.font.size = Pt(size); r.bold = ri in bold_rows
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 and align_first_left else WD_ALIGN_PARAGRAPH.CENTER
    # cegah baris terpecah
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit"); trPr.append(cs)
    if note:
        para(note, italic=True, size=8, after=6)
    else:
        para("", after=2, size=4)
    return t


def figure(path, width_cm, caption):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(1); p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    para(caption, size=9, align="c", after=6)


def figure2(p1, p2, w_cm, caption):
    t = doc.add_table(rows=1, cols=2); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c, pth in zip(t.rows[0].cells, (p1, p2)):
        c.width = Cm(w_cm + 0.3)
        pp = c.paragraphs[0]; pp.alignment = WD_ALIGN_PARAGRAPH.CENTER; pp.paragraph_format.space_after = Pt(0)
        pp.add_run().add_picture(str(pth), width=Cm(w_cm))
    trPr = t.rows[0]._tr.get_or_add_trPr(); trPr.append(OxmlElement("w:cantSplit"))
    para(caption, size=9, align="c", after=6)


def footer_pagenum():
    p = sec.footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(); r.font.size = Pt(9)
    for t, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if t:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), t); r._r.append(e)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt; r._r.append(e)


footer_pagenum()

# -------------------------------------------------------------- judul
para("Evaluasi Fitur Lag dan Rata-rata Bergulir pada Peramalan Energi Listrik Harian Satu Rumah Tangga: "
     "Validasi Kronologis, Optimisme Validasi Acak, dan Kebijakan Data Hilang", bold=True, align="c", size=14, after=2)
para("Evaluating Lag-Based Feature Engineering for Short-Term Household Electricity Consumption Forecasting",
     italic=True, align="c", size=11, after=4)
para("[Nama Anggota 1], [Nama Anggota 2], [Nama Anggota 3]", align="c", size=10.5, after=0)
para("Program Sarjana Terapan Teknik Informatika, Politeknik Elektronika Negeri Surabaya (PENS) · Mata kuliah TTKI, Proyek P4",
     align="c", size=9.5, after=6)

# ------------------------------------------------------------- abstrak
abs_id = (
    f"Peramalan konsumsi listrik satu rumah tangga sering dievaluasi dengan protokol pembagian data dan penanganan data hilang "
    f"yang tidak dijelaskan. Penelitian ini menguji fitur kalender (skenario A), lag 1 dan 7 hari (B), serta rata-rata bergulir "
    f"7 dan 14 hari (C) untuk peramalan energi harian satu hari ke depan pada dataset Individual Household Electric Power "
    f"Consumption (salinan Kaggle). Pembanding berupa baseline naïve dan seasonal naïve, dua model (Ridge Regression dan "
    f"gradient boosting), dan satu skenario ablasi. Hyperparameter dipilih pada validation 2009; data uji 2010 ({ntest} hari) "
    f"dievaluasi satu kali dengan walk-forward, dengan interval bootstrap blok dan uji Diebold–Mariano berkoreksi Holm. "
    f"Seluruh skenario mengungguli seasonal naïve (MAE {f(sn.mae)} kWh/hari). MAE terendah {f(best.mae)} kWh/hari "
    f"(gradient boosting, skenario C) turun {dn(best.delta_vs_snaive_pct)} dari seasonal naïve dan "
    f"{dn(best.delta_vs_A_pct)} dari kalender saja, tetapi keunggulan atas kalender saja belum signifikan setelah koreksi "
    f"Holm. K-fold teracak tidak konsisten lebih optimistis daripada walk-forward pada hari uji yang sama. Mengisi data hilang "
    f"dengan nol lebih buruk daripada imputasi kausal pada {n_worse} dari {len(e3)} konfigurasi, namun tidak signifikan setelah koreksi. "
    f"Hasil terbatas pada satu rumah tangga dan satu periode uji."
)
abs_en = (
    f"Single-household electricity forecasts are often evaluated with unreported data-splitting and missing-data choices. "
    f"We evaluate calendar features (scenario A), 1- and 7-day lags (B), and 7- and 14-day rolling means (C) for one-day-ahead "
    f"daily energy forecasting on the Individual Household Electric Power Consumption dataset (Kaggle copy), against naïve and "
    f"seasonal-naïve baselines, with Ridge regression and gradient boosting and one ablation. Hyperparameters were tuned on 2009; "
    f"the 2010 test set ({ntest} days) was evaluated once by walk-forward, with block-bootstrap intervals and Holm-adjusted "
    f"Diebold–Mariano tests. Every scenario beat seasonal naïve (MAE {f(sn.mae,2)} kWh/day). The best MAE, {f(best.mae,2)} kWh/day "
    f"(gradient boosting, scenario C), is {dn(best.delta_vs_snaive_pct)} below seasonal naïve and "
    f"{dn(best.delta_vs_A_pct)} below calendar-only, but the gain over calendar-only is not significant after Holm correction. "
    f"Shuffled K-fold was not consistently more optimistic than walk-forward on identical test days. Zero-filling gaps was worse "
    f"than causal imputation in {n_worse} of {len(e3)} configurations, though not significant after correction. Findings are limited "
    f"to one household and one test period."
)
words = lambda t: len(t.split())
print("kata abstrak ID/EN:", words(abs_id), words(abs_en))
assert 150 <= words(abs_id) <= 250 and 150 <= words(abs_en) <= 250
p = para("", align="j", after=2); add_runs(p, "Abstrak. ", bold=True, size=9.5); add_runs(p, abs_id, size=9.5)
p = para("", align="j", after=2); add_runs(p, "Abstract. ", bold=True, size=9.5); add_runs(p, abs_en, italic=True, size=9.5)
p = para("", after=4); add_runs(p, "Kata kunci: ", bold=True, size=9.5)
add_runs(p, "peramalan konsumsi listrik; fitur lag; walk-forward; seasonal naïve; data hilang; validasi deret waktu", size=9.5)

# --------------------------------------------------------- 1 Pendahuluan
h1("1. Pendahuluan")
body("Peramalan konsumsi listrik rumah tangga jangka pendek dipakai untuk manajemen energi dan perencanaan beban, tetapi beban satu "
     "rumah tangga sangat fluktuatif dan penuh ketidakpastian (Kong et al., 2019). Karena itu banyak studi memakai "
     "model pembelajaran mendalam; Kim dan Cho (2019), misalnya, memakai CNN-LSTM dan melaporkan RMSE terendah dibanding metode "
     "konvensional pada data konsumsi daya rumah tangga UCI. Fortuna et al. (2025) menelaah kontribusi kelompok fitur pada peramalan "
     "listrik rumah tangga, termasuk pada dataset UCI Household.")
body("Kualitas evaluasi sama pentingnya dengan pilihan model. Hewamalage et al. (2023) mendokumentasikan praktik evaluasi keliru "
     "yang membuat metode yang tidak kompetitif tampak kompetitif, antara lain pembanding yang tidak sesuai pola musiman. Cerqueira "
     "et al. (2020) mencatat bahwa validasi silang mengacak urutan waktu dan dapat memberi estimasi yang tidak realistis, sedangkan "
     "Bergmeir et al. (2018) menunjukkan K-fold masih sah untuk model autoregresif murni dengan galat tak berkorelasi. Bergmeir dan "
     "Benítez (2012) menyoroti jurang antara evaluasi deret waktu tradisional dan validasi silang pada pembelajaran mesin. Ketidakpastian "
     "ini perlu diuji pada data nyata, bukan diasumsikan.")
body("Data rumah tangga juga hampir selalu tidak lengkap. Hussain et al. (2025) melaporkan bahwa data hilang acak menurunkan akurasi "
     "peramalan beban LSTM dan bahwa imputasi berbasis pembelajaran mesin umumnya lebih baik daripada imputasi statistik, sedangkan "
     "Manoj (2025, pracetak) membandingkan metode pengisian celah struktural pada satu rumah tangga dan menemukan imputasi musiman "
     "lebih menjaga sebaran data daripada interpolasi linear. Pada dataset UCI yang dipakai di sini, perlakuan data hilang jarang "
     "dilaporkan sebagai faktor eksperimen. Berdasarkan penelusuran terbatas pada sumber-sumber di atas, kandidat celah penelitian "
     "adalah: belum ditemukan evaluasi yang memisahkan kontribusi lag dan rata-rata bergulir terhadap baseline seasonal naïve pada satu "
     "rumah tangga dengan validasi kronologis, perbandingan dengan validasi acak pada hari uji yang identik, dan kebijakan data hilang "
     "yang dibandingkan secara eksplisit (kandidat gap yang memerlukan verifikasi penelusuran yang lebih luas sebelum diklaim sebagai kebaruan).")
body("Penelitian ini menjawab tiga pertanyaan. RQ1: seberapa besar fitur lag dan rata-rata bergulir menurunkan galat peramalan energi "
     "harian dibanding baseline naïve, seasonal naïve, dan fitur kalender saja? RQ2: seberapa jauh K-fold teracak lebih optimistis "
     "daripada walk-forward pada hari uji yang sama? RQ3: apakah kesimpulan RQ1 bertahan terhadap kebijakan data hilang? Hipotesis: "
     "H1, fitur historis menurunkan MAE terhadap kalender saja; H2, K-fold teracak memberi MAE lebih rendah daripada walk-forward; "
     "H3, mengisi data hilang dengan nol memperburuk MAE. Kontribusi: (i) ablasi bertingkat lima konfigurasi fitur dengan dua model "
     "dan dua baseline pada himpunan hari yang sama, disertai inferensi berpasangan; (ii) pengukuran optimisme validasi acak pada hari "
     "yang identik; (iii) analisis sensitivitas empat kebijakan data hilang; dan (iv) repositori yang dapat direproduksi.")

# ------------------------------------------------------------- 2 Metode
h1("2. Metode")
figure(FIG / "fig1_flow.png", 15.6, "Gambar 1. Alur eksperimen dari data mentah sampai inferensi. Hyperparameter dikunci sebelum data uji dievaluasi.")
h2("2.1 Dataset dan asal data")
d0 = ds.set_index("split")
body("Data berasal dari Individual Household Electric Power Consumption (Hébrail & Bérard, 2012; UCI, DOI 10.24432/C58K54) melalui "
     "salinan Kaggle uciml/electric-power-consumption-data-set (diunduh tim pada 12 November 2026; lisensi di Kaggle: Open Database "
     "License untuk basis data dan Database Contents License untuk isinya). Dataset memuat 2.075.259 pengukuran per menit dari satu "
     "rumah tangga di Prancis, 16 Desember 2006 sampai 26 November 2010; 1,252% baris hilang pada semua kolom sekaligus. "
     "Eksperimen memakai agregasi harian dari berkas Kaggle tersebut (jumlah daya aktif dan jumlah menit valid per hari) yang dihasilkan "
     "skrip audit tim; integritasnya diperiksa (1.442 hari berurutan, menit valid ditambah hilang sama dengan 1.440 pada setiap hari). "
     "Lingkungan eksekusi tidak dapat mengunduh Kaggle, sehingga agregasi ulang dari data menit tersedia di src/make_daily.py untuk verifikasi independen.")
h2("2.2 Target, kebijakan data hilang, dan pembagian data")
body("Unit observasi adalah hari. Global_active_power berunit kW, sehingga energi harian (kWh) adalah jumlah Global_active_power/60 atas menit "
     "valid. Empat kebijakan data hilang dibandingkan pada deret yang dipakai untuk fitur dan pelatihan: P1 (utama) menskalakan hari dengan "
     "hilang ≤10% ke 1.440 menit dan menjadikan hari lainnya NaN yang dibuang; P2 hanya memakai hari lengkap; P3 seperti P1 tetapi NaN pada deret "
     "fitur diisi nilai hari yang sama pada minggu-minggu sebelumnya (t−7, t−14, t−21; kausal); P4 menjumlahkan menit valid tanpa penskalaan dan menganggap "
     "menit hilang bernilai nol. Target yang dinilai selalu target P1 yang teramati, sehingga tidak ada nilai imputasi yang ikut dinilai.")
rows = []
nm = {"train": "Train", "validation": "Validation", "test": "Test"}
per = {"train": "16 Des 2006 – 31 Des 2008", "validation": "1 Jan – 31 Des 2009", "test": "1 Jan – 26 Nov 2010"}
for k in ("train", "validation", "test"):
    r = d0.loc[k]
    rows.append([nm[k], per[k], int(r.n_days), int(r.n_nan_days), int(r.n_eval_days), f"{f(r.mean_kwh,2)} ± {f(r.sd_kwh,2)}"])
table(["Bagian", "Periode", "Hari", "Hari NaN", "Hari dievaluasi", "Rerata ± sd (kWh/hari)"], rows, [2.2, 4.6, 1.5, 1.8, 2.7, 3.8],
      caption="Tabel 1. Pembagian kronologis dan karakteristik data (P1; hari dievaluasi = target teramati dan seluruh fitur historis valid).")
figure(FIG / "fig2_daily_series.png", 15.0, "Gambar 2. Energi harian dan pembagian kronologis. Garis merah di dasar menandai hari NaN (>10% menit hilang).")
h2("2.3 Baseline, skenario fitur, dan model")
body("Baseline naïve memakai konsumsi kemarin dan seasonal naïve memakai konsumsi tujuh hari sebelumnya. Skenario A memakai kalender (hari "
     "dalam minggu dan bulan, one-hot); B menambahkan lag 1 dan lag 7; C menambahkan rata-rata bergulir 7 dan 14 hari; R (ablasi) memakai A "
     "ditambah rata-rata bergulir tanpa lag. Prediksi hari t hanya memakai data hari ≤ t−1: lag dibuat dengan shift(k), dan rata-rata "
     "bergulir dihitung dari deret yang sudah digeser sehari dengan jendela penuh. Sifat ini diuji otomatis dengan perturbasi masa depan, "
     "termasuk kontrol negatif pada fitur yang sengaja bocor (src/check_leakage.py). Model: Ridge Regression (dengan StandardScaler yang di-fit hanya pada data latih) "
     "dan gradient boosting berbasis histogram (Friedman, 2001; implementasi scikit-learn, Pedregosa et al., 2011). Semua baseline dan skenario dinilai pada "
     "himpunan hari yang sama.")
h2("2.4 Tuning dan protokol evaluasi")
body("Hyperparameter dipilih per model dan skenario pada validation 2009 memakai protokol yang sama dengan uji: walk-forward dengan jendela "
     "yang diperluas, model dilatih ulang tiap 7 hari, dan peramalan satu hari ke depan memakai riwayat aktual. Grid Ridge α ∈ {1, 10, 30, 100, 300, 1000, 3000}; "
     "gradient boosting 150 iterasi, learning rate {0,05; 0,1}, kedalaman {1, 2, 3}, minimum sampel per daun {10, 25}. Grid awal yang terlalu sempit "
     "(optimum di tepi) diperluas berdasarkan validation saja dan dicatat di docs/decisions.md. Setelah hyperparameter terkunci, data uji "
     "dievaluasi satu kali dengan walk-forward yang sama (jendela diperluas dari awal data, termasuk validation).")
body("Untuk RQ2, K-fold teracak (5 fold, 10 pengulangan) dijalankan pada seluruh hari berfitur lengkap dari semua periode dengan hyperparameter yang sama; galat out-of-fold "
     "dibatasi pada hari uji himpunan P1 sehingga hari yang dibandingkan identik dengan walk-forward. Metrik: MAE (utama), RMSE, dan MASE "
     f"berskala MAE seasonal naïve dalam sampel pada train ({f(S['mase_scale_kwh'],2)} kWh; Hyndman & Koehler, 2006). Inferensi memakai selisih galat "
     "absolut berpasangan: interval 95% dengan moving-block bootstrap (blok 7 hari, 10.000 replikasi; Künsch, 1989), uji Diebold–Mariano dengan koreksi "
     "Harvey et al. (1997) dan variansi Newey–West (Diebold & Mariano, 1995), serta koreksi Holm dalam keluarga 20 kontras yang ditetapkan sebelum evaluasi uji "
     "(8 skenario vs seasonal naïve, 8 kontras antarskenario, 4 kontras antarmodel). Seluruh keputusan dibekukan di docs/decisions.md sebelum data uji dievaluasi.")

# ------------------------------------------------------------- 3 Hasil
h1("3. Hasil")
h2("3.1 Validation")
body(f"Pada validation (333 hari), seasonal naïve (MAE {f(vsn)}) lebih baik daripada naïve ({f(vnv)}). MAE walk-forward Ridge turun dari "
     f"{f(val('Ridge','A'))} (A) ke {f(val('Ridge','B'))} (B) dan {f(val('Ridge','C'))} (C); skenario ablasi R mencapai {f(val('Ridge','R'))}. "
     f"Pada gradient boosting nilainya {f(val('HGB','A'))}, {f(val('HGB','B'))}, {f(val('HGB','C'))}, dan {f(val('HGB','R'))} untuk A, B, C, dan R "
     f"(results/validation_best.csv). Pada validation, rata-rata bergulir saja (R) sudah menyamai atau melampaui lag-plus-rolling (C) pada Ridge.")
h2("3.2 Hasil uji dan RQ1")
body(f"Pada data uji ({ntest} hari), seluruh skenario dan kedua model mengungguli kedua baseline (Tabel 2, Gambar 3a). MAE turun dari "
     f"{f(nv.mae)} (naïve) dan {f(sn.mae)} (seasonal naïve) menjadi {f(best.mae)} pada gradient boosting skenario C, yaitu "
     f"{dn(best.delta_vs_snaive_pct)} di bawah seasonal naïve. Terhadap kalender saja pada model yang sama, B menurunkan MAE "
     f"{dn(rB.delta_vs_A_pct)} (Ridge) dan {dn(gB.delta_vs_A_pct)} (gradient boosting), C menurunkan {dn(rC.delta_vs_A_pct)} dan "
     f"{dn(gC.delta_vs_A_pct)}, dan R menurunkan {dn(rR.delta_vs_A_pct)} dan {dn(gR.delta_vs_A_pct)}.")
rows = []
order = [("baseline", "naive", "Naïve", ""), ("baseline", "seasonal_naive", "Seasonal naïve", "")]
for m, mn in (("Ridge", "Ridge"), ("HGB", "Grad. boosting")):
    for s, sl in (("A", "A kalender"), ("B", "B +lag"), ("C", "C +lag+rolling"), ("R", "R rolling saja")):
        order.append((m, s, mn, sl))
for m, s, mn, sl in order:
    r = M(m, s)
    rows.append([mn if m != "baseline" else sl or mn, "" if m == "baseline" else sl, f"{f(r.mae)} [{f(r.mae_ci_lo,2)}; {f(r.mae_ci_hi,2)}]",
                 f(r.rmse), f(r.mase, 2), "–" if m == "baseline" and s == "seasonal_naive" else pct(r.delta_vs_snaive_pct),
                 "–" if m == "baseline" else pct(r.delta_vs_A_pct)])
table(["Model", "Skenario", "MAE [CI 95%]", "RMSE", "MASE", "Δ vs seasonal", "Δ vs A"], rows, [2.8, 2.9, 3.6, 1.4, 1.3, 2.3, 1.9], size=8,
      caption=f"Tabel 2. Kesalahan prediksi pada data uji, walk-forward (n = {ntest} hari; satuan kWh/hari).",
      note="CI: moving-block bootstrap pada galat absolut. Δ: perubahan MAE relatif terhadap seasonal naïve atau terhadap skenario A pada model yang sama.")
sw = lambda m, s: C(f"{m}-{s} vs seasonal_naive")
sn_rows = [sw(m, s_) for m in ("Ridge", "HGB") for s_ in "ABCR"]
assert all(r.ci_lo > 0 for r in sn_rows), "klaim: interval tidak memuat nol"
n_sn_holm = sum(r.p_holm < 0.05 for r in sn_rows)
assert n_sn_holm == 6
body(f"Perbaikan terhadap seasonal naïve konsisten: pada delapan kontras, selisih MAE berpasangan berkisar {f(min(sw(m,s).diff_kwh for m in ('Ridge','HGB') for s in 'ABCR'),2)} "
     f"sampai {f(max(sw(m,s).diff_kwh for m in ('Ridge','HGB') for s in 'ABCR'),2)} kWh/hari dan interval 95% tidak memuat nol pada semuanya; "
     f"{n_sn_holm} dari delapan tetap signifikan setelah koreksi Holm (untuk kalender saja p Holm = {pv(sw('Ridge','A').p_holm)} dan {pv(sw('HGB','A').p_holm)}). "
     "Perbaikan terhadap kalender saja lebih kecil dan kurang pasti (Tabel 3).")
rows = []
for m, mn in (("Ridge", "Ridge"), ("HGB", "Grad. boosting")):
    for a_, b_ in (("B", "A"), ("C", "A"), ("R", "A"), ("C", "B")):
        r = C(f"{m}: {a_} vs {b_}")
        rows.append([f"{mn}: {a_} vs {b_}", f"{f(r.diff_kwh,3)} [{f(r.ci_lo,2)}; {f(r.ci_hi,2)}]", pct(-r.rel_reduction_pct), pv(r.p), pv(r.p_holm)])
table(["Kontras (kandidat vs pembanding)", "Selisih MAE kWh/hari [CI 95%]", "Δ MAE", "p (DM)", "p Holm"], rows, [4.6, 4.6, 2.0, 2.0, 2.0],
      caption="Tabel 3. Kontras antarskenario pada data uji (selisih positif: kandidat lebih baik; keluarga Holm: 20 kontras).")
body(f"Pada Ridge, C dibanding A memberi selisih {f(C('Ridge: C vs A').diff_kwh,2)} kWh/hari (CI [{f(C('Ridge: C vs A').ci_lo,2)}; {f(C('Ridge: C vs A').ci_hi,2)}]); pada "
     f"gradient boosting {f(C('HGB: C vs A').diff_kwh,2)} (CI [{f(C('HGB: C vs A').ci_lo,2)}; {f(C('HGB: C vs A').ci_hi,2)}]). Kedua interval tidak memuat nol, tetapi p setelah "
     f"koreksi Holm adalah {pv(C('Ridge: C vs A').p_holm)} dan {pv(C('HGB: C vs A').p_holm)}. Penambahan rata-rata bergulir pada B (C vs B) tidak jelas pada gradient boosting "
     f"(selisih {f(C('HGB: C vs B').diff_kwh,3)}), dan selisih gradient boosting dengan Ridge pada skenario C ({f(C('C: HGB vs Ridge').diff_kwh,2)} kWh/hari) "
     f"juga memuat nol dalam intervalnya.")

h2("3.3 Optimisme validasi acak (RQ2)")
rows = []
for m, mn in (("Ridge", "Ridge"), ("HGB", "Grad. boosting")):
    for s in "ABCR":
        o = O(m, s)
        rows.append([f"{mn} {s}", f(o.mae_walkforward), f"{f(o.mae_kfold_mean)} ± {f(o.mae_kfold_sd,3)}",
                     f"{f(o.optimism_kwh,3)} [{f(o.optimism_ci_lo,2)}; {f(o.optimism_ci_hi,2)}]", pct(o.optimism_pct, 1, True), pv(o.p), pv(o.p_holm)])
table(["Konfigurasi", "MAE walk-forward", "MAE K-fold (rerata ± sd, 10 ulang)", "Selisih [CI 95%]", "Optimisme", "p", "p Holm"], rows,
      [2.7, 2.1, 3.8, 3.4, 1.8, 1.3, 1.5], size=7.5,
      caption=f"Tabel 4. Walk-forward versus K-fold teracak (5 fold) pada {ntest} hari uji yang identik (kWh/hari).",
      note="Selisih = MAE walk-forward − MAE K-fold; positif berarti validasi acak lebih optimistis. Holm: 8 konfigurasi.")
oA = [O("Ridge", "A"), O("HGB", "A")]
gk = lambda m: opt[(opt.model == m) & (opt.scenario == "C")].gain_vs_A_kfold_pct.iloc[0]
gw = lambda m: opt[(opt.model == m) & (opt.scenario == "C")].gain_vs_A_walkforward_pct.iloc[0]
body(f"K-fold teracak hanya lebih optimistis pada skenario A: {pct(oA[0].optimism_pct,1,True)} (Ridge) dan {pct(oA[1].optimism_pct,1,True)} (gradient boosting), "
     f"dengan interval 95% yang tidak memuat nol tetapi p Holm {pv(oA[0].p_holm)} dan {pv(oA[1].p_holm)}. Pada skenario dengan fitur historis selisihnya mendekati nol atau "
     f"berlawanan arah (gradient boosting B: {pct(O('HGB','B').optimism_pct,1,True)}). Akibatnya manfaat skenario C terhadap A justru tampak lebih kecil pada K-fold "
     f"({pct(gk('HGB'))} versus {pct(gw('HGB'))} pada gradient boosting; {pct(gk('Ridge'))} versus {pct(gw('Ridge'))} pada Ridge).")

figure2(FIG / "fig3_mae_ci.png", FIG / "fig5_optimism.png", 7.4, "Gambar 3. (a) MAE uji dengan interval 95% bootstrap blok; (b) selisih MAE walk-forward − K-fold teracak pada hari uji yang sama (kanan nol: validasi acak lebih optimistis).")
h2("3.4 Kebijakan data hilang (RQ3)")
body(f"Perbandingan dilakukan pada tiga himpunan hari: E1 ({S['n_E1']} hari; P1, P3, P4), E3 ({S['n_E3']} hari, termasuk hari yang jendela fiturnya menyentuh celah data; P3 dan P4), dan E2 "
     f"({S['n_E2']} hari; keempat kebijakan, tetapi fitur identik karena jendelanya hanya berisi hari lengkap). Pada E1 dan E2 perbedaan antarkebijakan sangat kecil "
     f"(selisih MAE per konfigurasi maksimum {f(max_e12,2)} kWh/hari; interval 95% tidak memuat nol pada {n_e12_nz} dari {n_e12} kontras non-degeneratif; results/policy_contrasts.csv). Efek kebijakan muncul pada E3 (Tabel 5): "
     f"zero-fill (P4) lebih buruk daripada imputasi kausal (P3) pada {n_worse} dari {len(e3)} konfigurasi, dengan selisih {f(e3_rng[0],2)}–{f(e3_rng[1],2)} kWh/hari; "
     f"interval 95% tidak memuat nol pada {int((e3.ci_hi < 0).sum())} konfigurasi ({n_sig_raw} dengan p<0,05), tetapi p Holm terkecil {pv(min_holm)}.")
rows = []
lab = {("baseline", "naive"): "Naïve", ("baseline", "seasonal_naive"): "Seasonal naïve"}
for _, r in e3.iterrows():
    k = (r.model, r.scenario)
    name = lab.get(k, f"{'Ridge' if r.model == 'Ridge' else 'Grad. boosting'} {r.scenario}")
    rows.append([name, f(P("E3", "P3", r.model, r.scenario).mae), f(P("E3", "P4", r.model, r.scenario).mae),
                 f"{f(-r.diff_kwh,3)} [{f(-r.ci_hi,2)}; {f(-r.ci_lo,2)}]", pv(r.p), pv(r.p_holm)])
table(["Konfigurasi", "MAE P3 (imputasi)", "MAE P4 (zero-fill)", "Tambahan galat P4 [CI 95%]", "p", "p Holm"], rows,
      [3.4, 2.6, 2.6, 4.0, 1.6, 1.6], size=8,
      caption=f"Tabel 5. Zero-fill versus imputasi kausal pada E3 ({S['n_E3']} hari uji; kWh/hari).",
      note="Tambahan galat = MAE P4 − MAE P3 per hari (positif: zero-fill lebih buruk); keluarga Holm: 10 kontras.")
rr, rg = G("E3", "P4", "Ridge", "R"), G("E3", "P4", "HGB", "R")
r3, g3 = G("E3", "P3", "Ridge", "R"), G("E3", "P3", "HGB", "R")
body(f"Pada E3 manfaat fitur juga berubah: di bawah P3, R menurunkan MAE terhadap A sebesar {dn(r3.gain_vs_A_pct)} (Ridge) dan {dn(g3.gain_vs_A_pct)} (gradient boosting), tetapi di bawah P4 "
     f"R justru menambah MAE sebesar {dn(rr.gain_vs_A_pct)} dan {dn(rg.gain_vs_A_pct)}. Sebaliknya, C tetap lebih baik daripada A pada semua kebijakan dan himpunan "
     f"(Δ MAE C vs A berkisar {pct(c_gain.max())} sampai {pct(c_gain.min())}).")

h2("3.5 Analisis residual")
body(f"Konfigurasi yang dipilih dari validation di antara skenario A–C adalah Ridge C (MAE validation {f(val('Ridge','C'))}). Galatnya terbesar pada akhir pekan: MAE Sabtu "
     f"{f(dow.mae[5],2)} dan Minggu {f(dow.mae[6],2)} kWh/hari, dibanding {f(dow.mae[4],2)} pada Jumat dan rata-rata {f(wd,2)} pada hari kerja (Gambar 4). "
     f"Residual rata-rata negatif pada Minggu ({f(dow.mean_resid[6],2)}) dan Jumat ({f(dow.mean_resid[4],2)}), yaitu prediksi cenderung terlalu tinggi, dan positif pada Senin "
     f"({f(dow.mean_resid[0],2)}). Residual keseluruhan rata-rata {f(S['residual_acf']['mean_resid'],2)} kWh/hari dengan autokorelasi lag-1 {f(S['residual_acf']['lag1'],2)} dan lag-7 "
     f"{f(S['residual_acf']['lag7'],2)}, sehingga tidak tampak struktur linear yang tersisa pada lag tersebut.")
figure(FIG / "fig4_actual_pred_dow.png", 15.0, "Gambar 4. Aktual versus prediksi Ridge C pada data uji (kiri; celah = hari tidak dievaluasi) dan MAE per hari dalam minggu (kanan).")

# --------------------------------------------------------- 4 Pembahasan
h1("4. Pembahasan")
h2("4.1 Fitur historis (H1)")
body(f"H1 didukung secara arah dan moderat dalam besarnya. Keunggulan atas seasonal naïve kuat dan bertahan setelah koreksi Holm, tetapi sebagian besarnya sudah dicapai oleh "
     f"kalender saja (A menurunkan MAE sekitar {dn(rA.delta_vs_snaive_pct)}–{dn(gA.delta_vs_snaive_pct)} terhadap seasonal naïve). Tambahan dari lag dan rata-rata bergulir "
     f"({dn(rC.delta_vs_A_pct)} pada Ridge dan {dn(gC.delta_vs_A_pct)} pada gradient boosting) memiliki interval yang menjauhi nol, tetapi tidak lolos koreksi atas 20 kontras. "
     f"Dengan {ntest} hari uji yang berautokorelasi, bukti ini sebaiknya dibaca sebagai indikatif. Pada ablasi, R (rata-rata bergulir tanpa lag) memperoleh sekitar {int(round(100*rR.delta_vs_A_pct/rC.delta_vs_A_pct))}% (Ridge) dan {int(round(100*gR.delta_vs_A_pct/gC.delta_vs_A_pct))}% (gradient boosting) "
     f"dari penurunan MAE skenario C, yang masuk akal karena rata-rata bergulir meredam fluktuasi harian; mekanisme ini tidak diuji. "
     f"Peringkat model tidak stabil: gradient boosting unggul pada B dan C, tetapi tidak berbeda nyata dari Ridge, dan pada validation Ridge R justru terbaik.")
h2("4.2 Validasi acak (H2)")
body("H2 tidak didukung sebagaimana dirumuskan. Optimisme K-fold hanya terlihat pada kalender saja dan kecil (sekitar 2%), sedangkan pada skenario berfitur lag arahnya tidak konsisten. "
     "Hasil ini selaras dengan Bergmeir et al. (2018): bila fitur hanya memuat masa lalu dan galat model hampir tak berkorelasi, K-fold tidak merusak estimasi secara besar. "
     "Namun hasil ini tidak membenarkan K-fold sebagai praktik umum. Cerqueira et al. (2020) dan Hewamalage et al. (2023) mengingatkan bahwa kecocokan bergantung pada kestasioneran, dan "
     "tren turun konsumsi pada data ini (rerata harian 26,65, 25,90, dan 25,44 kWh pada train, validation, dan test) serta residual uji yang cenderung negatif mengindikasikan bahwa "
     "ketidakstasioneran ringan ada. Walk-forward tetap protokol yang menjawab pertanyaan operasional (meramal masa depan dari masa lalu), dan pada penelitian ini ia memberi estimasi manfaat fitur yang lebih besar, bukan lebih kecil.")
h2("4.3 Data hilang (H3) dan baseline")
body(f"H3 searah tetapi belum terbukti: zero-fill memberi galat lebih besar pada {n_worse} dari {len(e3)} konfigurasi pada hari yang jendelanya menyentuh celah data, dan paling merugikan "
     "fitur yang menghitung rata-rata bergulir (skenario R) serta baseline seasonal naïve. Mekanisme yang masuk akal (tidak diuji): nol menurunkan nilai lag dan rata-rata bergulir hingga 14 hari setelah celah, "
     "sehingga fitur menyiratkan konsumsi rendah yang tidak terjadi. Hasil ini sejalan dengan temuan Hussain et al. (2025) bahwa data hilang menurunkan akurasi peramalan, meskipun jenis "
     "data, model, dan metode pengisiannya berbeda. Pada hari yang tidak terkena celah, ketiga kebijakan hampir identik, sehingga kebijakan data hilang lebih berpengaruh pada "
     f"cakupan (E3 mencakup {S['n_E3']} hari, E1 hanya {S['n_E1']}) daripada pada kesimpulan utama. Perhatikan pula bahwa peringkat baseline berbalik: seasonal naïve lebih baik daripada naïve pada validation "
     f"({f(vsn,2)} berbanding {f(vnv,2)}), tetapi lebih buruk pada uji ({f(sn.mae,2)} berbanding {f(nv.mae,2)}); karena itu kedua baseline sebaiknya dilaporkan bersamaan.")
h2("4.4 Keterbatasan")
body(f"(1) Satu rumah tangga dan satu periode uji (Januari–November 2010) sehingga generalisasi terbatas. (2) {330 - ntest} dari 330 hari uji tidak dinilai karena target hilang atau jendela fitur tidak lengkap. "
     "(3) Interval dan uji berasumsi stasioneritas lemah dan hanya memakai satu rangkaian uji; kontras berpasangan dikoreksi Holm sehingga konservatif. "
     "(4) Grid hyperparameter terbatas dan optimum gradient boosting skenario A berada di tepi atas kedalaman. (5) Tidak ada variabel eksternal seperti cuaca dan hari libur, padahal galat akhir pekan "
     "paling besar. (6) Penjelasan mekanisme dalam Pembahasan adalah dugaan yang tidak diuji. (7) Agregasi harian diambil dari keluaran skrip audit tim, bukan diagregasi ulang di lingkungan eksekusi. "
     "(8) Penelusuran literatur terbatas pada sekitar 15 sumber sehingga klaim celah penelitian belum final.")

# ---------------------------------------------------------- 5 Kesimpulan
h1("5. Kesimpulan")
body(f"Pada satu rumah tangga UCI, fitur kalender, lag, dan rata-rata bergulir semuanya mengungguli baseline naïve dan seasonal naïve pada walk-forward 2010; MAE terendah {f(best.mae,2)} kWh/hari "
     f"(gradient boosting C) turun {dn(best.delta_vs_snaive_pct)} dari seasonal naïve dan {dn(best.delta_vs_A_pct)} dari kalender saja, tetapi keunggulan atas kalender saja belum signifikan setelah koreksi "
     "Holm (RQ1, H1 moderat). K-fold teracak tidak secara konsisten lebih optimistis daripada walk-forward pada hari uji yang sama (RQ2, H2 tidak didukung). Zero-fill konsisten memberi galat lebih "
     "besar daripada imputasi kausal pada hari dekat celah data, namun belum signifikan setelah koreksi (RQ3, H3 searah). Penelitian lanjutan perlu menambah rumah tangga dan periode uji, "
     "memakai variabel eksternal (cuaca, hari libur), dan memverifikasi agregasi harian dari data menit mentah.")

h1("Ketersediaan Data dan Kode")
body("Data: Kaggle uciml/electric-power-consumption-data-set, salinan dataset UCI (Hébrail & Bérard, 2012; doi:10.24432/C58K54); lisensi di Kaggle: Open Database License dan Database Contents License; data mentah tidak "
     "disertakan. Kode, hasil, dan catatan keputusan: repositori GitHub kelompok (tag versi final: [isi setelah rilis]). Seed: 42 (model), 100–109 (K-fold), 7 (bootstrap). "
     "Lingkungan: Python 3.13, pandas 3.0.5, numpy 2.5.3, scikit-learn 1.9.1, scipy 1.18.1 (environment-freeze.txt). Urutan menjalankan: check_leakage, run_validation, run_test, run_random_cv, analyze, make_figures.")
h1("Pernyataan Penggunaan AI")
body("Asisten AI (Claude, Anthropic) dipakai untuk merancang protokol eksperimen, menulis dan menjalankan kode di lingkungan sandbox, menelusuri dan memeriksa metadata referensi melalui pencarian web, "
     "serta menyusun draf naskah. Seluruh angka pada naskah dihasilkan langsung dari berkas results/ oleh skrip proyek. Penulis bertanggung jawab atas isi naskah dan [konfirmasi penulis: telah menjalankan ulang "
     "seluruh skrip dan memeriksa kesesuaian hasil sebelum pengumpulan].")

h1("Referensi")
refs = [
    "Bergmeir, C., & Benítez, J. M. (2012). On the use of cross-validation for time series predictor evaluation. Information Sciences, 191, 192–213. https://doi.org/10.1016/j.ins.2011.12.028",
    "Bergmeir, C., Hyndman, R. J., & Koo, B. (2018). A note on the validity of cross-validation for evaluating autoregressive time series prediction. Computational Statistics & Data Analysis, 120, 70–83. https://doi.org/10.1016/j.csda.2017.11.003",
    "Cerqueira, V., Torgo, L., & Mozetič, I. (2020). Evaluating time series forecasting models: An empirical study on performance estimation methods. Machine Learning, 109(11), 1997–2028. https://doi.org/10.1007/s10994-020-05910-7",
    "Diebold, F. X., & Mariano, R. S. (1995). Comparing predictive accuracy. Journal of Business & Economic Statistics, 13(3), 253–263. https://doi.org/10.1080/07350015.1995.10524599",
    "Fortuna, C., Cerar, G., Bertalanič, B., Čampa, A., & Mohorčič, M. (2025). Data model design for explainable machine learning-based electricity applications. arXiv:2505.23607.",
    "Friedman, J. H. (2001). Greedy function approximation: A gradient boosting machine. The Annals of Statistics, 29(5), 1189–1232. https://doi.org/10.1214/aos/1013203451",
    "Harvey, D., Leybourne, S., & Newbold, P. (1997). Testing the equality of prediction mean squared errors. International Journal of Forecasting, 13(2), 281–291. https://doi.org/10.1016/S0169-2070(96)00719-4",
    "Hébrail, G., & Bérard, A. (2012). Individual household electric power consumption [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C58K54",
    "Hewamalage, H., Ackermann, K., & Bergmeir, C. (2023). Forecast evaluation for data scientists: Common pitfalls and best practices. Data Mining and Knowledge Discovery, 37, 788–832. https://doi.org/10.1007/s10618-022-00894-5",
    "Hussain, A., Giangrande, P., Franchini, G., Fenili, L., & Messi, S. (2025). Analyzing the effect of error estimation on random missing data patterns in mid-term electrical forecasting. Electronics, 14(7), 1383. https://doi.org/10.3390/electronics14071383",
    "Hyndman, R. J., & Koehler, A. B. (2006). Another look at measures of forecast accuracy. International Journal of Forecasting, 22(4), 679–688. https://doi.org/10.1016/j.ijforecast.2006.03.001",
    "Kim, T.-Y., & Cho, S.-B. (2019). Predicting residential energy consumption using CNN-LSTM neural networks. Energy, 182, 72–81. https://doi.org/10.1016/j.energy.2019.05.230",
    "Kong, W., Dong, Z. Y., Jia, Y., Hill, D. J., Xu, Y., & Zhang, Y. (2019). Short-term residential load forecasting based on LSTM recurrent neural network. IEEE Transactions on Smart Grid, 10(1), 841–851. https://doi.org/10.1109/TSG.2017.2753802",
    "Künsch, H. R. (1989). The jackknife and the bootstrap for general stationary observations. The Annals of Statistics, 17(3), 1217–1241. https://doi.org/10.1214/aos/1176347265",
    "Manoj, M. (2025). Robust probabilistic load forecasting for a single household: A comparative study from SARIMA to Transformers on the REFIT dataset. arXiv:2512.00856.",
    "Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825–2830.",
]
for i, r in enumerate(refs, 1):
    p = para(r, size=8.5, after=1)
    p.paragraph_format.left_indent = Cm(0.7); p.paragraph_format.first_line_indent = Cm(-0.7)

doc.save(OUT)
print("tersimpan:", OUT)
