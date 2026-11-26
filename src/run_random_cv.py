"""Pembanding RQ2: K-fold teracak (5 fold x 10 pengulangan) pada seluruh hari berfitur lengkap (kebijakan P1).

Prediksi out-of-fold dibatasi pada hari uji himpunan evaluasi E1 sehingga hari yang dibandingkan identik dengan
walk-forward. Hyperparameter tetap dari validation. Ini BUKAN evaluasi utama; hanya untuk mengukur optimisme.

Keluaran: results/randomcv_predictions.csv  (repeat, model, scenario, date, y_true, y_pred)
Jalankan dari root repo:  python src/run_random_cv.py
"""
import json

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

from common import (MODELS, RESULTS, SCEN_COLS, SCENARIOS, SPLITS, build_series, eval_mask, load_daily,
                    make_features, make_model)

N_REPEATS, N_FOLDS, SEED0 = 10, 5, 100
d = load_daily()
ser = build_series(d)
feat = make_features(ser["P1"]["feat"])
selected = json.load(open(RESULTS / "selected_hyperparams.json"))

pool = eval_mask(feat, ser["score"], SPLITS["train"][0], SPLITS["test"][1])
pool_days = pool.index[pool]
test_lo, test_hi = map(pd.Timestamp, SPLITS["test"])
is_test = (pool_days >= test_lo) & (pool_days <= test_hi)
y = ser["P1"]["train"].loc[pool_days].to_numpy()

rows = []
for rep in range(N_REPEATS):
    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED0 + rep)
    for model in MODELS:
        for scen in SCENARIOS:
            X = feat.loc[pool_days, SCEN_COLS[scen]].to_numpy()
            oof = np.full(len(pool_days), np.nan)
            for tr, te in kf.split(X):
                m = make_model(model, selected[f"{model}|{scen}"])
                m.fit(X[tr], y[tr])
                oof[te] = m.predict(X[te])
            rows.append(pd.DataFrame({"repeat": rep, "model": model, "scenario": scen,
                                      "date": pool_days[is_test], "y_true": y[is_test], "y_pred": oof[is_test]}))
    print("pengulangan", rep, "selesai", flush=True)
pd.concat(rows).to_csv(RESULTS / "randomcv_predictions.csv", index=False)
print("hari pool:", len(pool_days), "| hari uji:", int(is_test.sum()))
