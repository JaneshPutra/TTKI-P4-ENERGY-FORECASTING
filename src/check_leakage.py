"""Uji kebocoran informasi (Buku Petunjuk §5.4).

1. Fitur hari t tidak berubah bila y[t:] diganti nilai acak (masa depan tidak boleh bocor ke fitur).
2. Imputasi kausal (P3) pada hari < t tidak berubah bila y[t:] diganti.
3. Prediksi walk-forward untuk blok sebelum tanggal T tidak berubah bila seluruh data >= T diacak.
4. Ridge: scaler hanya belajar dari data latih (diperiksa lewat prediksi yang identik pada poin 3).

Jalankan: python src/check_leakage.py   (keluar dengan kode 1 jika ada uji gagal)
"""
import sys

import numpy as np
import pandas as pd

from common import (SCEN_COLS, build_series, causal_seasonal_fill, check_input, load_daily,
                    make_features, walk_forward, RESULTS)

rng = np.random.default_rng(0)
d = load_daily()
ser = build_series(d)
y = ser["P1"]["feat"]
fails = []

# 1. fitur
f0 = make_features(y)
for t in rng.choice(np.arange(30, len(y) - 1), size=40, replace=False):
    y2 = y.copy()
    y2.iloc[t:] = rng.uniform(0, 100, size=len(y) - t)
    f2 = make_features(y2)
    a = f0.iloc[: t + 1].drop(columns=[]).to_numpy()
    b = f2.iloc[: t + 1].to_numpy()
    if not np.allclose(a, b, equal_nan=True):
        fails.append(f"fitur berubah pada t={t}")
print("[1] fitur kausal: OK" if not [x for x in fails if x.startswith("fitur")] else "[1] GAGAL")

# 2. imputasi kausal
base = causal_seasonal_fill(ser["P1"]["feat"])
for t in rng.choice(np.arange(30, len(y) - 1), size=40, replace=False):
    y2 = ser["P1"]["feat"].copy()
    y2.iloc[t:] = rng.uniform(0, 100, size=len(y) - t)
    filled = causal_seasonal_fill(y2)
    if not np.allclose(base.iloc[:t].to_numpy(), filled.iloc[:t].to_numpy(), equal_nan=True):
        fails.append(f"imputasi tidak kausal t={t}")
print("[2] imputasi kausal: OK" if not [x for x in fails if x.startswith("imputasi")] else "[2] GAGAL")

# 3. walk-forward tidak melihat masa depan
T = pd.Timestamp("2009-07-01")
for model, params in (("Ridge", {"alpha": 10}), ("HGB", {"learning_rate": 0.1, "max_depth": 2, "min_samples_leaf": 10})):
    for scen in ("C",):
        feat = make_features(ser["P1"]["feat"])
        wf0 = walk_forward(feat, ser["P1"]["train"], ser["score"], model, params, scen, "2009-01-01", "2009-12-31")
        yy = ser["P1"]["feat"].copy()
        tr = ser["P1"]["train"].copy()
        m = yy.index >= T
        yy[m] = rng.uniform(0, 100, size=m.sum())
        tr[m] = rng.uniform(0, 100, size=m.sum())
        sc = ser["score"].copy()
        sc[m] = rng.uniform(0, 100, size=m.sum())
        feat2 = make_features(yy)
        wf1 = walk_forward(feat2, tr, sc, model, params, scen, "2009-01-01", "2009-12-31")
        # blok yang seluruhnya < T: origin 2009-01-01 + 7k, blok berakhir sebelum T
        cut = T - pd.Timedelta(days=7)
        a = wf0.loc[wf0.index < cut, "y_pred"]
        b = wf1.loc[wf1.index < cut, "y_pred"]
        if not (len(a) > 0 and np.allclose(a.to_numpy(), b.to_numpy())):
            fails.append(f"walk-forward {model} bocor")
print("[3] walk-forward tanpa kebocoran masa depan: OK" if not [x for x in fails if x.startswith("walk")] else "[3] GAGAL")

info = check_input(d)
print("[4] integritas masukan:", info)
if not (info["contiguous"] and info["minutes_sum_ok"] and info["rescale_max_abs_diff"] < 1e-9):
    fails.append("integritas masukan")

RESULTS.mkdir(exist_ok=True)
with open(RESULTS / "leakage_check.txt", "w") as fh:
    fh.write("fails: " + (", ".join(fails) if fails else "none") + "\n")
    fh.write(str(info) + "\n")
if fails:
    print("GAGAL:", fails)
    sys.exit(1)
print("Semua uji lolos.")
