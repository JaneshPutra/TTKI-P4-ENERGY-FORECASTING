"""Agregasi data menit mentah (UCI/Kaggle) menjadi energi harian, untuk verifikasi independen.

Pemakaian (dari root repo):
    python src/make_daily.py data/raw/household_power_consumption.txt --out data/daily_energy_regen.csv --compare

Kolom keluaran sama dengan data/daily_energy_from_kaggle.csv:
    date, energy_kwh_raw, valid_minutes, missing_minutes, complete, energy_kwh
  - energy_kwh_raw = jumlah (Global_active_power / 60) atas menit valid   [kWh; menit hilang dianggap nol]
  - valid_minutes  = jumlah menit dengan Global_active_power teramati
  - missing_minutes = 1440 - valid_minutes (menit absen dari berkas juga dihitung hilang)
  - energy_kwh     = kebijakan P1: raw * 1440 / valid_minutes bila valid >= 90%, selain itu NaN
Opsi --compare membandingkan dengan data/daily_energy_from_kaggle.csv dan melaporkan selisih maksimum.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def aggregate(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", na_values=["?", ""], low_memory=False,
                     usecols=["Date", "Time", "Global_active_power"])
    df["ts"] = pd.to_datetime(df["Date"] + " " + df["Time"], format="%d/%m/%Y %H:%M:%S")
    df["gap"] = pd.to_numeric(df["Global_active_power"], errors="coerce")
    df = df.drop_duplicates("ts").set_index("ts").sort_index()
    day = df.index.floor("D")
    valid = df["gap"].notna().groupby(day).sum()
    raw = (df["gap"].fillna(0) / 60).groupby(day).sum()
    out = pd.DataFrame({"energy_kwh_raw": raw, "valid_minutes": valid.astype(int)})
    out = out.reindex(pd.date_range(out.index.min(), out.index.max(), freq="D"), fill_value=0)
    out["valid_minutes"] = out["valid_minutes"].astype(int)
    out["missing_minutes"] = 1440 - out["valid_minutes"]
    out["complete"] = out["valid_minutes"] == 1440
    e = out["energy_kwh_raw"] * 1440 / out["valid_minutes"].replace(0, np.nan)
    out["energy_kwh"] = e.where(out["valid_minutes"] >= 0.9 * 1440)
    out.index.name = "date"
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("--out", default=str(ROOT / "data" / "daily_energy_regen.csv"))
    ap.add_argument("--compare", action="store_true")
    a = ap.parse_args()
    d = aggregate(a.raw)
    d.to_csv(a.out)
    print("hari:", len(d), "| hari NaN (P1):", int(d.energy_kwh.isna().sum()))
    if a.compare:
        ref = pd.read_csv(ROOT / "data" / "daily_energy_from_kaggle.csv", parse_dates=["date"]).set_index("date")
        j = d.join(ref, lsuffix="_new", rsuffix="_ref", how="outer")
        for c in ("energy_kwh_raw", "valid_minutes", "energy_kwh"):
            diff = (j[f"{c}_new"] - j[f"{c}_ref"]).abs().max()
            print(f"selisih maksimum {c}: {diff:.3e}")
        print("hari berbeda status NaN:", int((j.energy_kwh_new.isna() != j.energy_kwh_ref.isna()).sum()))
