"""Modul bersama: pemuatan data harian, kebijakan data hilang, fitur, metrik, walk-forward.

Semua keputusan mengikuti docs/decisions.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "daily_energy_from_kaggle.csv"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"

SEED = 42
REFIT_EVERY = 7  # hari
SPLITS = {
    "train": ("2006-12-16", "2008-12-31"),
    "validation": ("2009-01-01", "2009-12-31"),
    "test": ("2010-01-01", "2010-11-26"),
}
POLICIES = ["P1", "P2", "P3", "P4"]
SCENARIOS = ["A", "B", "C", "R"]
MODELS = ["Ridge", "HGB"]

GRIDS = {
    "Ridge": [{"alpha": a} for a in (1, 10, 30, 100, 300, 1000, 3000)],
    "HGB": [
        {"learning_rate": lr, "max_depth": md, "min_samples_leaf": ml}
        for lr in (0.05, 0.1)
        for md in (1, 2, 3)
        for ml in (10, 25)
    ],
}


# --------------------------------------------------------------- data harian
def load_daily() -> pd.DataFrame:
    d = pd.read_csv(DATA, parse_dates=["date"]).set_index("date")
    d.index.freq = "D"
    return d


def check_input(d: pd.DataFrame) -> dict:
    """Pemeriksaan integritas berkas harian."""
    out = {
        "n_days": int(len(d)),
        "start": str(d.index.min().date()),
        "end": str(d.index.max().date()),
        "contiguous": bool((d.index.to_series().diff().dropna() == pd.Timedelta("1D")).all()),
        "minutes_sum_ok": bool(((d.valid_minutes + d.missing_minutes) == 1440).all()),
    }
    ok = d.dropna(subset=["energy_kwh"])
    out["rescale_max_abs_diff"] = float(
        (ok.energy_kwh_raw * 1440 / ok.valid_minutes - ok.energy_kwh).abs().max()
    )
    return out


def build_series(d: pd.DataFrame) -> dict[str, dict[str, pd.Series]]:
    """Untuk tiap kebijakan: deret fitur ('feat') dan deret target latih ('train').

    Skor selalu memakai target P1 teramati ('score').
    """
    raw = d["energy_kwh_raw"]
    vm = d["valid_minutes"]
    p1 = raw * 1440 / vm
    p1 = p1.where(vm >= 0.9 * 1440)  # >10% hilang -> NaN
    p2 = raw.where(vm == 1440)
    p3_feat = causal_seasonal_fill(p1)
    p4 = raw.copy()  # zero-fill: menit hilang dianggap nol, tanpa penskalaan
    return {
        "P1": {"feat": p1, "train": p1},
        "P2": {"feat": p2, "train": p2},
        "P3": {"feat": p3_feat, "train": p1},
        "P4": {"feat": p4, "train": p4},
        "score": p1,
    }


def causal_seasonal_fill(s: pd.Series) -> pd.Series:
    """Isi NaN secara kausal: nilai terisi pada t-7, t-14, t-21; jika kosong, nilai valid terakhir.

    Nilai pada hari t hanya memakai hari < t, sehingga tidak ada informasi masa depan.
    """
    v = s.to_numpy(dtype=float).copy()
    n = len(v)
    last = np.nan
    for i in range(n):
        if np.isnan(v[i]):
            fill = np.nan
            for k in (7, 14, 21):
                if i - k >= 0 and not np.isnan(v[i - k]):
                    fill = v[i - k]
                    break
            if np.isnan(fill):
                fill = last
            v[i] = fill
        if not np.isnan(v[i]):
            last = v[i]
    return pd.Series(v, index=s.index, name=s.name)


# --------------------------------------------------------------------- fitur
def make_features(y: pd.Series) -> pd.DataFrame:
    """Semua kolom fitur. Hari t hanya memakai y[<= t-1]."""
    idx = y.index
    f = pd.DataFrame(index=idx)
    dow = pd.Categorical(idx.dayofweek, categories=range(7))
    mon = pd.Categorical(idx.month, categories=range(1, 13))
    for k in range(7):
        f[f"dow_{k}"] = (dow == k).astype(float)
    for m in range(1, 13):
        f[f"mon_{m}"] = (mon == m).astype(float)
    f["lag1"] = y.shift(1)
    f["lag7"] = y.shift(7)
    sh = y.shift(1)
    f["roll7"] = sh.rolling(7, min_periods=7).mean()
    f["roll14"] = sh.rolling(14, min_periods=14).mean()
    f["naive"] = y.shift(1)
    f["snaive"] = y.shift(7)
    return f


CAL = [f"dow_{k}" for k in range(7)] + [f"mon_{m}" for m in range(1, 13)]
SCEN_COLS = {
    "A": CAL,
    "B": CAL + ["lag1", "lag7"],
    "C": CAL + ["lag1", "lag7", "roll7", "roll14"],
    "R": CAL + ["roll7", "roll14"],
}
# kolom historis yang wajib valid agar hari masuk himpunan evaluasi (sama untuk semua skenario)
HIST_COLS = ["lag1", "lag7", "roll7", "roll14"]


def make_model(name: str, params: dict):
    if name == "Ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=params["alpha"]))
    if name == "HGB":
        return HistGradientBoostingRegressor(
            max_iter=150,
            early_stopping=False,
            random_state=SEED,
            **params,
        )
    raise ValueError(name)


# -------------------------------------------------------------------- metrik
def mae(a, p) -> float:
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(p))))


def rmse(a, p) -> float:
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(p)) ** 2)))


# ------------------------------------------------------------- walk-forward
def eval_mask(feat: pd.DataFrame, score: pd.Series, lo: str, hi: str) -> pd.Series:
    """Hari dalam [lo, hi] dengan target teramati dan seluruh fitur historis valid."""
    m = score.notna() & feat[HIST_COLS].notna().all(axis=1)
    m &= (score.index >= pd.Timestamp(lo)) & (score.index <= pd.Timestamp(hi))
    return m


def walk_forward(
    feat: pd.DataFrame,
    train_y: pd.Series,
    score_y: pd.Series,
    model_name: str,
    params: dict,
    scenario: str,
    lo: str,
    hi: str,
    refit_every: int = REFIT_EVERY,
) -> pd.DataFrame:
    """Walk-forward expanding window, satu-hari-ke-depan dengan riwayat aktual.

    Pada tiap origin r (tiap `refit_every` hari) model dilatih pada semua hari d < r
    dengan target latih valid dan fitur skenario valid, lalu meramal hari r .. r+refit_every-1
    yang masuk himpunan evaluasi. Mengembalikan DataFrame (date, y_true, y_pred).
    """
    cols = SCEN_COLS[scenario]
    X = feat[cols]
    ev = eval_mask(feat, score_y, lo, hi)
    days = ev.index[ev]
    if len(days) == 0:
        return pd.DataFrame(columns=["y_true", "y_pred"])
    origin = pd.Timestamp(lo)
    end = pd.Timestamp(hi)
    rows = []
    train_ok = train_y.notna() & X.notna().all(axis=1)
    while origin <= end:
        block_end = min(origin + pd.Timedelta(days=refit_every - 1), end)
        blk = days[(days >= origin) & (days <= block_end)]
        if len(blk):
            tr_idx = train_ok.index[train_ok & (train_ok.index < origin)]
            mdl = make_model(model_name, params)
            mdl.fit(X.loc[tr_idx].to_numpy(), train_y.loc[tr_idx].to_numpy())
            pred = mdl.predict(X.loc[blk].to_numpy())
            rows.append(pd.DataFrame({"y_true": score_y.loc[blk].to_numpy(), "y_pred": pred}, index=blk))
        origin = block_end + pd.Timedelta(days=1)
    out = pd.concat(rows) if rows else pd.DataFrame(columns=["y_true", "y_pred"])
    out.index.name = "date"
    return out
