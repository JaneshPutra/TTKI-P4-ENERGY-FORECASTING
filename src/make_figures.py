"""Gambar untuk paper. Membaca results/*.csv. Jalankan dari root repo: python src/make_figures.py"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from common import FIGURES, RESULTS, SPLITS, build_series, load_daily

FIGURES.mkdir(exist_ok=True)
BLUE, ORANGE, AQUA, GRAY, DARK, LIGHT = "#257de0", "#f47230", "#00b894", "#8a8a8a", "#191919", "#e6e6e6"
plt.rcParams.update({"font.size": 8, "font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#666666", "axes.labelcolor": DARK,
                     "xtick.color": DARK, "ytick.color": DARK, "axes.grid": True, "grid.color": LIGHT,
                     "grid.linewidth": 0.6, "axes.axisbelow": True, "savefig.dpi": 300, "savefig.bbox": "tight"})
COL = {"Ridge": BLUE, "HGB": ORANGE}
NAME = {"A": "A kalender", "B": "B +lag", "C": "C +lag+rolling", "R": "R rolling saja"}

d = load_daily()
ser = build_series(d)
met = pd.read_csv(RESULTS / "metrics_primary.csv")
tp = pd.read_csv(RESULTS / "test_predictions.csv", parse_dates=["date"])

# ---- Gambar 1: alur eksperimen
fig, ax = plt.subplots(figsize=(7.0, 2.5))
ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(0, 36)
boxes = [
    (1, 20, 15, 12, "Data Kaggle\n(UCI, per menit)\n2,08 juta baris"),
    (19, 20, 15, 12, "Agregasi harian\nkWh = Σ kW/60,\nskala ke 1.440 mnt"),
    (37, 20, 17, 12, "4 kebijakan data\nhilang P1–P4\n(deret fitur)"),
    (57, 20, 17, 12, "Fitur A, B, C, R\n(lag dan rolling,\ngeser 1 hari)"),
    (77, 20, 21, 12, "Tuning di validation\n(walk-forward 2009,\nrefit 7 hari)"),
]
for x, y, w, h, t in boxes:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.5", fc="#eef4fc", ec=BLUE, lw=1))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=7)
for (x1, w1), (x2, _) in zip([(b[0], b[2]) for b in boxes[:-1]], [(b[0], b[2]) for b in boxes[1:]]):
    ax.annotate("", xy=(x2 - 0.2, 26), xytext=(x1 + w1 + 0.4, 26), arrowprops=dict(arrowstyle="-|>", color=DARK, lw=1))
boxes2 = [
    (77, 2, 21, 12, "Hyperparameter\nterkunci"),
    (50, 2, 23, 12, "Test 2010 sekali:\nwalk-forward (utama)\n+ K-fold teracak"),
    (21, 2, 25, 12, "MAE, RMSE, MASE;\nbootstrap blok, DM,\nHolm"),
    (1, 2, 16, 12, "RQ1, RQ2, RQ3\nresidual"),
]
for x, y, w, h, t in boxes2:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.5", fc="#fef1ea", ec=ORANGE, lw=1))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=7)
ax.annotate("", xy=(87.5, 14.6), xytext=(87.5, 19.6), arrowprops=dict(arrowstyle="-|>", color=DARK, lw=1))
for xa, xb in ((77, 73.4), (50, 46.4), (21, 17.4)):
    ax.annotate("", xy=(xb, 8), xytext=(xa - 0.4, 8), arrowprops=dict(arrowstyle="-|>", color=DARK, lw=1))
fig.savefig(FIGURES / "fig1_flow.png"); plt.close(fig)

# ---- Gambar 2: deret harian dan split
s = ser["score"]
fig, ax = plt.subplots(figsize=(7.0, 2.3))
for name, (lo, hi), c in (("Train", SPLITS["train"], "#f2f2f2"), ("Validation", SPLITS["validation"], "#dfeaf8"),
                          ("Test", SPLITS["test"], "#fde6d9")):
    ax.axvspan(pd.Timestamp(lo), pd.Timestamp(hi), color=c, lw=0)
    ax.text(pd.Timestamp(lo) + (pd.Timestamp(hi) - pd.Timestamp(lo)) / 2, 66, name, ha="center", fontsize=8, color=DARK)
ax.plot(s.index, s.values, color=DARK, lw=0.6)
nan = s[s.isna()].index
ax.plot(nan, np.full(len(nan), 1.5), "|", color="#c0392b", ms=7, mew=1.2, label=f"hari NaN (>10% hilang), n={len(nan)}")
ax.set_ylim(0, 70); ax.set_ylabel("Energi harian (kWh)")
ax.legend(loc="upper right", frameon=False, fontsize=7, bbox_to_anchor=(1.0, 0.88))
fig.savefig(FIGURES / "fig2_daily_series.png"); plt.close(fig)

# ---- Gambar 3: MAE uji dengan CI 95% (blok bootstrap)
order = [("baseline", "seasonal_naive", "Seasonal naïve"), ("baseline", "naive", "Naïve")]
for m in ("Ridge", "HGB"):
    for sc in "ABCR":
        order.append((m, sc, f"{'Ridge' if m == 'Ridge' else 'GB'} {NAME[sc]}"))
fig, ax = plt.subplots(figsize=(3.45, 3.0))
for i, (m, sc, lab) in enumerate(order[::-1]):
    r = met[(met.model == m) & (met.scenario == sc)].iloc[0]
    c = GRAY if m == "baseline" else COL[m]
    ax.plot([r.mae_ci_lo, r.mae_ci_hi], [i, i], color=c, lw=1.6)
    ax.plot(r.mae, i, "o", color=c, ms=5, mec="white", mew=0.8)
    ax.text(r.mae_ci_hi + 0.12, i, f"{r.mae:.2f}", va="center", fontsize=7)
ax.set_yticks(range(len(order))); ax.set_yticklabels([o[2] for o in order[::-1]], fontsize=7)
ax.set_xlabel("MAE uji (kWh/hari), CI 95% bootstrap blok"); ax.set_xlim(3.2, 8.2); ax.grid(axis="y", visible=False)
fig.savefig(FIGURES / "fig3_mae_ci.png"); plt.close(fig)

# ---- Gambar 4: aktual vs prediksi (Ridge-C) dan MAE per hari
b = tp[(tp.policy == "P1") & (tp.model == "Ridge") & (tp.scenario == "C")].set_index("date").sort_index()
res = pd.read_csv(RESULTS / "residual_by_dow.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.4), gridspec_kw={"width_ratios": [2.3, 1]})
full = pd.date_range(b.index.min(), b.index.max())
a1.plot(full, b.y_true.reindex(full), color=DARK, lw=0.8, label="Aktual")
a1.plot(full, b.y_pred.reindex(full), color=BLUE, lw=0.8, label="Prediksi Ridge-C")
a1.set_ylabel("Energi harian (kWh)"); a1.legend(frameon=False, fontsize=7, ncol=2, loc="upper right")
a1.set_ylim(0, 58)
a1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b")); a1.set_xlabel("2010")
lab = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
a2.bar(range(7), res.mae, color=[BLUE if k < 5 else ORANGE for k in range(7)], width=0.65)
a2.set_xticks(range(7)); a2.set_xticklabels(lab, fontsize=7); a2.set_ylabel("MAE (kWh/hari)")
for k, v in enumerate(res.mae):
    a2.text(k, v + 0.1, f"{v:.1f}", ha="center", fontsize=6.5)
a2.grid(axis="x", visible=False)
fig.tight_layout(); fig.savefig(FIGURES / "fig4_actual_pred_dow.png"); plt.close(fig)

# ---- Gambar 5: optimisme validasi acak
opt = pd.read_csv(RESULTS / "optimism_randomcv.csv")
fig, ax = plt.subplots(figsize=(3.45, 2.5))
labels = []
y = 0
for m in ("Ridge", "HGB"):
    for sc in "ABCR":
        r = opt[(opt.model == m) & (opt.scenario == sc)].iloc[0]
        ax.plot([r.optimism_ci_lo, r.optimism_ci_hi], [y, y], color=COL[m], lw=1.6)
        ax.plot(r.optimism_kwh, y, "o", color=COL[m], ms=5, mec="white", mew=0.8)
        labels.append(f"{'Ridge' if m == 'Ridge' else 'GB'} {sc}")
        y += 1
ax.axvline(0, color=DARK, lw=0.8)
ax.set_yticks(range(8)); ax.set_yticklabels(labels, fontsize=7); ax.invert_yaxis()
ax.set_xlabel("MAE walk-forward − MAE K-fold (kWh/hari)\n>0: validasi acak lebih optimistis")
ax.grid(axis="y", visible=False)
fig.savefig(FIGURES / "fig5_optimism.png"); plt.close(fig)

# ---- Gambar 6: kebijakan data hilang pada E3 (P3 vs P4)
pol = pd.read_csv(RESULTS / "policy_sensitivity.csv")
e3 = pol[pol["set"] == "E3"]
cfgs = [("baseline", "seasonal_naive", "Seas.\nnaïve"), ("baseline", "naive", "Naïve")] + \
       [(m, sc, f"{'Ridge' if m == 'Ridge' else 'GB'}\n{sc}") for m in ("Ridge", "HGB") for sc in "ABCR"]
fig, ax = plt.subplots(figsize=(7.0, 2.4))
w = 0.38
for j, (pcode, c, lab) in enumerate((("P3", BLUE, "P3 imputasi kausal"), ("P4", ORANGE, "P4 zero-fill"))):
    vals = [e3[(e3.policy == pcode) & (e3.model == m) & (e3.scenario == sc)].mae.iloc[0] for m, sc, _ in cfgs]
    ax.bar(np.arange(len(cfgs)) + (j - 0.5) * w, vals, width=w - 0.04, color=c, label=lab)
ax.set_xticks(range(len(cfgs))); ax.set_xticklabels([c[2] for c in cfgs], fontsize=7)
ax.set_ylabel("MAE (kWh/hari)"); ax.set_ylim(0, 7.6); ax.legend(frameon=False, fontsize=7, ncol=2, loc="upper right")
ax.grid(axis="x", visible=False)
fig.savefig(FIGURES / "fig6_policy_E3.png"); plt.close(fig)
print("gambar selesai")
