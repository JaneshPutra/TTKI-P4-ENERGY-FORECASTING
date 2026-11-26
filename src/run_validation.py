"""Tahap 1: pilih hyperparameter pada VALIDATION (2009) dengan walk-forward, kebijakan P1.

Data uji (2010) tidak disentuh di skrip ini.
Keluaran: results/validation_grid.csv, results/validation_baselines.csv, results/selected_hyperparams.json

Jalankan dari root repo:  python src/run_validation.py
"""
import json

import pandas as pd

from common import (GRIDS, MODELS, RESULTS, SCENARIOS, SPLITS, build_series, eval_mask, load_daily,
                    mae, make_features, rmse, walk_forward)

RESULTS.mkdir(exist_ok=True)
d = load_daily()
ser = build_series(d)
feat = make_features(ser["P1"]["feat"])
lo, hi = SPLITS["validation"]

rows = []
for model in MODELS:
    for scen in SCENARIOS:
        for params in GRIDS[model]:
            wf = walk_forward(feat, ser["P1"]["train"], ser["score"], model, params, scen, lo, hi)
            rows.append({"model": model, "scenario": scen, "params": json.dumps(params), "n_days": len(wf),
                         "val_mae": mae(wf.y_true, wf.y_pred), "val_rmse": rmse(wf.y_true, wf.y_pred)})
        print(model, scen, "selesai", flush=True)
grid = pd.DataFrame(rows)
grid.to_csv(RESULTS / "validation_grid.csv", index=False)

best = (grid.sort_values(["model", "scenario", "val_mae"]).groupby(["model", "scenario"], as_index=False).first())
selected = {f"{r.model}|{r.scenario}": json.loads(r.params) for r in best.itertuples()}
with open(RESULTS / "selected_hyperparams.json", "w") as fh:
    json.dump(selected, fh, indent=2)
best.to_csv(RESULTS / "validation_best.csv", index=False)

# baseline pada himpunan hari validation yang sama
ev = eval_mask(feat, ser["score"], lo, hi)
y = ser["score"][ev]
bl = pd.DataFrame({
    "baseline": ["naive", "seasonal_naive"],
    "n_days": int(ev.sum()),
    "val_mae": [mae(y, feat.loc[ev, "naive"]), mae(y, feat.loc[ev, "snaive"])],
    "val_rmse": [rmse(y, feat.loc[ev, "naive"]), rmse(y, feat.loc[ev, "snaive"])],
})
bl.to_csv(RESULTS / "validation_baselines.csv", index=False)
print(best.to_string())
print(bl.to_string())
