"""Utilitas inferensi untuk perbandingan galat berpasangan pada deret waktu."""
from __future__ import annotations

import numpy as np
from scipy import stats


def block_bootstrap_means(x: np.ndarray, block: int = 7, B: int = 10000, seed: int = 7) -> np.ndarray:
    """Distribusi bootstrap rata-rata dengan moving-block bootstrap (Künsch, 1989)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(B, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(B, nb * block)[:, :n]
    return x[idx].mean(axis=1)


def block_bootstrap_ci(x, block: int = 7, B: int = 10000, seed: int = 7, level: float = 0.95):
    bm = block_bootstrap_means(x, block, B, seed)
    a = (1 - level) / 2
    return float(np.quantile(bm, a)), float(np.quantile(bm, 1 - a))


def dm_test(d: np.ndarray, bandwidth: int = 7, h: int = 1):
    """Diebold–Mariano dengan koreksi Harvey–Leybourne–Newbold.

    d_t = L(e1_t) - L(e2_t). H0: E[d]=0. Variansi jangka panjang: Newey–West (kernel Bartlett).
    Mengembalikan (statistik terkoreksi, p dua sisi).
    """
    d = np.asarray(d, dtype=float)
    n = len(d)
    dbar = d.mean()
    dc = d - dbar
    lrv = float(np.dot(dc, dc) / n)
    for k in range(1, bandwidth + 1):
        gk = float(np.dot(dc[k:], dc[:-k]) / n)
        lrv += 2 * (1 - k / (bandwidth + 1)) * gk
    lrv = max(lrv, 1e-12)
    dm = dbar / np.sqrt(lrv / n)
    corr = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    stat = dm * corr
    p = 2 * (1 - stats.t.cdf(abs(stat), df=n - 1))
    return float(stat), float(p)


def holm(pvals: list[float]) -> list[float]:
    """Penyesuaian Holm–Bonferroni."""
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        val = (m - rank) * p[i]
        running = max(running, val)
        adj[i] = min(1.0, running)
    return adj.tolist()
