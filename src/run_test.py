"""Tahap 2: evaluasi walk-forward pada TEST (2010) untuk semua kebijakan data hilang, skenario, dan model.

Dijalankan sekali setelah docs/decisions.md dibekukan dan results/selected_hyperparams.json terkunci.
Keluaran: results/test_predictions.csv (format panjang), results/eval_days.csv

Jalankan dari root repo:  python src/run_test.py
"""
import json

import pandas as pd

from common import (MODELS, POLICIES, RESULTS, SCENARIOS, SPLITS, build_series, eval_mask, load_daily,
                    make_features, walk_forward)

d = load_daily()
ser = build_series(d)
selected = json.load(open(RESULTS / "selected_hyperparams.json"))
lo, hi = SPLITS["test"]

out, eval_rows = [], []
for pol in POLICIES:
    feat = make_features(ser[pol]["feat"])
    ev = eval_mask(feat, ser["score"], lo, hi)
    eval_rows.append(pd.DataFrame({"policy": pol, "date": ev.index[ev]}))
    days = ev.index[ev]
    # baseline dari deret fitur kebijakan tersebut
    for name, col in (("naive", "naive"), ("seasonal_naive", "snaive")):
        out.append(pd.DataFrame({"policy": pol, "model": "baseline", "scenario": name, "date": days,
                                 "y_true": ser["score"].loc[days].to_numpy(),
                                 "y_pred": feat.loc[days, col].to_numpy()}))
    for model in MODELS:
        for scen in SCENARIOS:
            params = selected[f"{model}|{scen}"]
            wf = walk_forward(feat, ser[pol]["train"], ser["score"], model, params, scen, lo, hi)
            wf = wf.reset_index().assign(policy=pol, model=model, scenario=scen)
            out.append(wf[["policy", "model", "scenario", "date", "y_true", "y_pred"]])
    print(pol, "selesai; hari dievaluasi:", int(ev.sum()), flush=True)

pd.concat(out).to_csv(RESULTS / "test_predictions.csv", index=False)
pd.concat(eval_rows).to_csv(RESULTS / "eval_days.csv", index=False)
print("Selesai.")
