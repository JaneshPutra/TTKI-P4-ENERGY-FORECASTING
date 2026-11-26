"""Analisis hasil: tabel metrik, inferensi berpasangan, optimisme validasi acak, sensitivitas data hilang.

Membaca results/test_predictions.csv, results/randomcv_predictions.csv, results/validation_*.csv.
Menulis results/*.csv dan results/summary.json (angka yang dipakai paper).

Jalankan dari root repo:  python src/analyze.py
"""
import json

import numpy as np
import pandas as pd

from common import (MODELS, RESULTS, SCENARIOS, SPLITS, build_series, eval_mask, load_daily, make_features, mae,
                    rmse)
from stats_utils import block_bootstrap_ci, dm_test, holm

B = 10000
d = load_daily()
ser = build_series(d)
feat1 = make_features(ser["P1"]["feat"])
tp = pd.read_csv(RESULTS / "test_predictions.csv", parse_dates=["date"])
rc = pd.read_csv(RESULTS / "randomcv_predictions.csv", parse_dates=["date"])
summary: dict = {}

# --------------------------------------------------------------- skala MASE
tr_lo, tr_hi = map(pd.Timestamp, SPLITS["train"])
s = ser["P1"]["feat"]
sn_err = (s - s.shift(7)).abs()
mase_scale = float(sn_err[(sn_err.index >= tr_lo) & (sn_err.index <= tr_hi)].dropna().mean())
summary["mase_scale_kwh"] = mase_scale

# ---------------------------------------------------------- tabel karakteristik
rows = []
for name, (lo, hi) in SPLITS.items():
    sl = ser["score"].loc[lo:hi]
    ev = eval_mask(feat1, ser["score"], lo, hi)
    n_days = len(sl)
    rows.append({"split": name, "start": lo, "end": hi, "n_days": n_days, "n_nan_days": int(sl.isna().sum()),
                 "n_eval_days": int(ev.sum()), "mean_kwh": float(sl.mean()), "sd_kwh": float(sl.std())})
pd.DataFrame(rows).to_csv(RESULTS / "dataset_table.csv", index=False)
summary["dataset"] = rows

# ------------------------------------------------------- galat primer (P1)
p1 = tp[tp.policy == "P1"].copy()
p1["abs_err"] = (p1.y_true - p1.y_pred).abs()
cfg = lambda m, s_: p1[(p1.model == m) & (p1.scenario == s_)].set_index("date").sort_index()
snv = cfg("baseline", "seasonal_naive")
nv = cfg("baseline", "naive")
days = snv.index
assert all(len(cfg(m, s_)) == len(days) for m in MODELS for s_ in SCENARIOS)
summary["n_test_eval_days"] = int(len(days))

metric_rows = []
for (m, s_), g in p1.groupby(["model", "scenario"]):
    g = g.sort_values("date")
    lo_, hi_ = block_bootstrap_ci(g.abs_err.to_numpy(), B=B)
    metric_rows.append({"model": m, "scenario": s_, "n": len(g), "mae": mae(g.y_true, g.y_pred),
                        "mae_ci_lo": lo_, "mae_ci_hi": hi_, "rmse": rmse(g.y_true, g.y_pred),
                        "mase": mae(g.y_true, g.y_pred) / mase_scale})
met = pd.DataFrame(metric_rows)
sn_mae = met[(met.model == "baseline") & (met.scenario == "seasonal_naive")].mae.iloc[0]
met["delta_vs_snaive_pct"] = 100 * (met.mae - sn_mae) / sn_mae
for m in MODELS:
    a = met[(met.model == m) & (met.scenario == "A")].mae.iloc[0]
    met.loc[met.model == m, "delta_vs_A_pct"] = 100 * (met.loc[met.model == m, "mae"] - a) / a
met.to_csv(RESULTS / "metrics_primary.csv", index=False)

# --------------------------------------------------------- kontras berpasangan
def contrast(e1: pd.Series, e2: pd.Series, label: str, note: str = "") -> dict:
    """d = |e1| - |e2| ; d>0 berarti kandidat 2 lebih baik. e1 pembanding, e2 kandidat."""
    dd = (e1 - e2).to_numpy()
    lo_, hi_ = block_bootstrap_ci(dd, B=B)
    stat, p = dm_test(dd)
    base = e1.mean()
    return {"contrast": label, "n": len(dd), "mae_ref": float(base), "mae_cand": float(e2.mean()),
            "diff_kwh": float(dd.mean()), "ci_lo": lo_, "ci_hi": hi_, "rel_reduction_pct": float(100 * dd.mean() / base),
            "rel_ci_lo": float(100 * lo_ / base), "rel_ci_hi": float(100 * hi_ / base), "dm_stat": stat, "p": p}

errs = {(m, s_): cfg(m, s_).abs_err for m in MODELS for s_ in SCENARIOS}
errs[("baseline", "seasonal_naive")] = snv.abs_err
errs[("baseline", "naive")] = nv.abs_err
crow = []
for m in MODELS:
    for s_ in SCENARIOS:
        crow.append(contrast(errs[("baseline", "seasonal_naive")], errs[(m, s_)], f"{m}-{s_} vs seasonal_naive"))
for m in MODELS:
    for hi_s, lo_s in (("B", "A"), ("C", "A"), ("C", "B"), ("R", "A")):
        crow.append(contrast(errs[(m, lo_s)], errs[(m, hi_s)], f"{m}: {hi_s} vs {lo_s}"))
for s_ in SCENARIOS:
    crow.append(contrast(errs[("Ridge", s_)], errs[("HGB", s_)], f"{s_}: HGB vs Ridge"))
con = pd.DataFrame(crow)
con["p_holm"] = holm(con.p.tolist())
con.to_csv(RESULTS / "contrasts_primary.csv", index=False)

# --------------------------- RQ2: optimisme validasi acak pada hari yang sama
rc["abs_err"] = (rc.y_true - rc.y_pred).abs()
rows = []
for (m, s_), g in rc.groupby(["model", "scenario"]):
    per_rep = g.groupby("repeat").apply(lambda x: mae(x.y_true, x.y_pred), include_groups=False)
    per_day = g.groupby("date").abs_err.mean().reindex(days)
    wf = errs[(m, s_)].reindex(days)
    dd = (wf - per_day).to_numpy()  # >0: validasi acak lebih optimistis (galat lebih kecil)
    lo_, hi_ = block_bootstrap_ci(dd, B=B)
    rows.append({"model": m, "scenario": s_, "mae_walkforward": float(wf.mean()), "mae_kfold_mean": float(per_rep.mean()),
                 "mae_kfold_sd": float(per_rep.std(ddof=1)), "optimism_kwh": float(dd.mean()),
                 "optimism_ci_lo": lo_, "optimism_ci_hi": hi_, "optimism_pct": float(100 * dd.mean() / wf.mean()),
                 "dm_stat": dm_test(dd)[0], "p": dm_test(dd)[1]})
opt = pd.DataFrame(rows)
opt["p_holm"] = holm(opt.p.tolist())
# manfaat fitur relatif terhadap A di bawah dua protokol
for m in MODELS:
    a_wf = opt[(opt.model == m) & (opt.scenario == "A")].mae_walkforward.iloc[0]
    a_kf = opt[(opt.model == m) & (opt.scenario == "A")].mae_kfold_mean.iloc[0]
    sel = opt.model == m
    opt.loc[sel, "gain_vs_A_walkforward_pct"] = 100 * (opt.loc[sel, "mae_walkforward"] - a_wf) / a_wf
    opt.loc[sel, "gain_vs_A_kfold_pct"] = 100 * (opt.loc[sel, "mae_kfold_mean"] - a_kf) / a_kf
opt.to_csv(RESULTS / "optimism_randomcv.csv", index=False)

# ------------------------------------ RQ3: sensitivitas kebijakan data hilang
# Himpunan evaluasi (semua memakai target P1 teramati):
#   E1 = hari evaluasi P1 (258)  : P1, P3, P4 punya prediksi
#   E3 = hari evaluasi P3 (314)  : P3, P4 punya prediksi (termasuk hari yang jendelanya menyentuh celah data)
#   E2 = hari evaluasi P2 (138)  : keempat kebijakan punya prediksi (jendela fitur hanya berisi hari lengkap)
ev_days = pd.read_csv(RESULTS / "eval_days.csv", parse_dates=["date"])
E = {k: pd.DatetimeIndex(ev_days[ev_days.policy == p_].date) for k, p_ in (("E1", "P1"), ("E2", "P2"), ("E3", "P3"))}
assert E["E2"].isin(E["E1"]).all() and E["E1"].isin(E["E3"]).all()
summary["n_E1"], summary["n_E2"], summary["n_E3"] = len(E["E1"]), len(E["E2"]), len(E["E3"])
SETS = {"E1": (E["E1"], ["P1", "P3", "P4"], "P1"), "E3": (E["E3"], ["P3", "P4"], "P3"), "E2": (E["E2"], ["P1", "P2", "P3", "P4"], "P1")}
tp["abs_err"] = (tp.y_true - tp.y_pred).abs()
configs = [(m, s_) for m in MODELS for s_ in SCENARIOS] + [("baseline", "naive"), ("baseline", "seasonal_naive")]
rows, prow = [], []
for sname, (days_s, pols, ref) in SETS.items():
    E_ = {}
    for pol in pols:
        for (m, s_) in configs:
            g = tp[(tp.policy == pol) & (tp.model == m) & (tp.scenario == s_)].set_index("date").sort_index().loc[days_s]
            E_[(pol, m, s_)] = g.abs_err
            rows.append({"set": sname, "policy": pol, "model": m, "scenario": s_, "n": len(g), "mae": g.abs_err.mean(),
                         "rmse": rmse(g.y_true, g.y_pred)})
    for (m, s_) in configs:
        for pol in pols:
            if pol == ref:
                continue
            r = contrast(E_[(ref, m, s_)], E_[(pol, m, s_)], f"{sname} {m}-{s_}: {pol} vs {ref}")
            r.update({"set": sname, "model": m, "scenario": s_, "policy": pol, "ref": ref})
            prow.append(r)
pol_df = pd.DataFrame(rows)
pol_df.to_csv(RESULTS / "policy_sensitivity.csv", index=False)
pc = pd.DataFrame(prow)
# keluarga uji H3 = E3: P4 vs P3 (10 konfigurasi). Kontras lain (E1, E2) deskriptif: banyak yang identik
# secara konstruksi (fitur sama), sehingga tidak dimasukkan ke koreksi Holm.
pc["p_holm"] = np.nan
m3 = pc["set"] == "E3"
pc.loc[m3, "p_holm"] = holm(pc.loc[m3, "p"].tolist())
pc.to_csv(RESULTS / "policy_contrasts.csv", index=False)
gain = []
for sname, (_, pols, _) in SETS.items():
    for pol in pols:
        for m in MODELS:
            sub = pol_df[(pol_df.set == sname) & (pol_df.policy == pol) & (pol_df.model == m)].set_index("scenario")
            for s_ in ("B", "C", "R"):
                gain.append({"set": sname, "policy": pol, "model": m, "scenario": s_,
                             "gain_vs_A_pct": 100 * (sub.loc[s_, "mae"] - sub.loc["A", "mae"]) / sub.loc["A", "mae"]})
pd.DataFrame(gain).to_csv(RESULTS / "policy_gain_vs_A.csv", index=False)
gain = pd.DataFrame(gain)

# --------------------------------- konfigurasi terbaik (dipilih dari validation)
vb = pd.read_csv(RESULTS / "validation_best.csv")
best = vb[vb.scenario.isin(["A", "B", "C"])].sort_values("val_mae").iloc[0]
summary["best_by_validation"] = {"model": best.model, "scenario": best.scenario, "val_mae": float(best.val_mae)}
bb = p1[(p1.model == best.model) & (p1.scenario == best.scenario)].set_index("date").sort_index()
bb["resid"] = bb.y_true - bb.y_pred
bb["dow"] = bb.index.dayofweek
bb["month"] = bb.index.month
res_dow = bb.groupby("dow").agg(n=("resid", "size"), mae=("abs_err", "mean"), mean_resid=("resid", "mean"))
res_dow.to_csv(RESULTS / "residual_by_dow.csv")
res_mon = bb.groupby("month").agg(n=("resid", "size"), mae=("abs_err", "mean"), mean_resid=("resid", "mean"))
res_mon.to_csv(RESULTS / "residual_by_month.csv")
r = bb.resid.to_numpy()
rc_ = r - r.mean()
acf = lambda k: float(np.dot(rc_[k:], rc_[:-k]) / np.dot(rc_, rc_))
summary["residual_acf"] = {"lag1": acf(1), "lag7": acf(7), "n": int(len(r)), "mean_resid": float(r.mean())}

# ------------------------------------------------------------- ringkasan
summary["test_period_mean_kwh"] = float(ser["score"].loc[SPLITS["test"][0]:SPLITS["test"][1]].mean())
with open(RESULTS / "summary.json", "w") as fh:
    json.dump(summary, fh, indent=2, default=float)

pd.set_option("display.width", 220)
print(met.round(3).to_string())
print(con.round(4).to_string())
print(opt.round(4).to_string())
print(pol_df.pivot_table(index=["set","model","scenario"],columns="policy",values="mae").round(3).to_string())
print(gain.round(2).to_string())
print(pc[["contrast", "diff_kwh", "ci_lo", "ci_hi", "p", "p_holm"]].round(4).to_string())
print(res_dow.round(3)); print(summary)
