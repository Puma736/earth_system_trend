"""Scientific algorithms for the Earth System Trend Detective.

All functions are pure NumPy/SciPy, vectorized where practical, and operate
on annual (or generic) time series of equal-length arrays.
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def _clean(values) -> np.ndarray:
    return np.asarray(values, dtype=float)


# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------

def linear_regression(years, values) -> dict:
    """OLS fit y = m*x + b with 95 % CI on the slope (Student-t)."""
    x, y = _clean(years), _clean(values)
    res = stats.linregress(x, y)
    n = len(x)
    t_crit = stats.t.ppf(0.975, n - 2) if n > 2 else 1.96
    half = float(t_crit * res.stderr)
    return {
        "slope_per_year": float(res.slope),
        "slope_per_decade": float(res.slope * 10),
        "intercept": float(res.intercept),
        "r_squared": float(res.rvalue**2),
        "p_value": float(res.pvalue),
        "ci95_slope_per_year": [float(res.slope - half), float(res.slope + half)],
        "is_significant": bool(res.pvalue < 0.05),
    }


def mann_kendall(values) -> dict:
    """Non-parametric Mann-Kendall trend test with tie correction."""
    x = _clean(values)
    n = len(x)
    s = int(np.sign(x[None, :] - x[:, None])[np.triu_indices(n, 1)].sum())
    _, counts = np.unique(x, return_counts=True)
    tie = float(np.sum(counts * (counts - 1) * (2 * counts + 5)))
    var_s = (n * (n - 1) * (2 * n + 5) - tie) / 18.0
    z = (s - np.sign(s)) / np.sqrt(var_s) if var_s > 0 else 0.0
    p = float(2 * (1 - stats.norm.cdf(abs(z))))
    significant = bool(p < 0.05)
    direction = "no_trend"
    if significant:
        direction = "increasing" if s > 0 else "decreasing"
    return {
        "S": s,
        "var_S": float(var_s),
        "z": float(z),
        "p_value": p,
        "is_significant": significant,
        "direction": direction,
    }


def sens_slope(years, values) -> dict:
    """Sen's slope: median of all pairwise slopes, per year and per decade."""
    t, x = _clean(years), _clean(values)
    i, j = np.triu_indices(len(x), 1)
    dt = t[j] - t[i]
    slopes = (x[j] - x[i]) / dt[dt > 0]
    per_year = float(np.median(slopes)) if len(slopes) else 0.0
    return {"per_year": per_year, "per_decade": per_year * 10.0}


# ---------------------------------------------------------------------------
# Anomalies
# ---------------------------------------------------------------------------

def z_scores(values, years=None, threshold: float = 2.0) -> dict:
    x = _clean(values)
    mu, sigma = float(x.mean()), float(x.std(ddof=1)) if len(x) > 1 else 0.0
    z = (x - mu) / sigma if sigma > 0 else np.zeros_like(x)
    items = []
    for idx, zv in enumerate(z):
        flag = "normal"
        if zv >= threshold:
            flag = "high_anomaly"
        elif zv <= -threshold:
            flag = "low_anomaly"
        items.append({
            "index": int(years[idx]) if years is not None else idx,
            "z": float(zv),
            "flag": flag,
        })
    return {
        "baseline_mean": mu,
        "baseline_std": sigma,
        "threshold": threshold,
        "n_outliers": int(sum(1 for i in items if i["flag"] != "normal")),
        "items": items,
    }


def historical_deviation(values, index: int = -1) -> dict:
    """D = X - mu and D% = (X - mu)/mu * 100 for the chosen point (latest)."""
    x = _clean(values)
    mu = float(x.mean())
    actual = float(x[index])
    d = actual - mu
    return {
        "baseline_mean": mu,
        "actual": actual,
        "deviation": float(d),
        "deviation_pct": float(d / mu * 100) if mu != 0 else None,
    }


# ---------------------------------------------------------------------------
# Correlations
# ---------------------------------------------------------------------------

def pearson(x, y) -> dict:
    r, p = stats.pearsonr(_clean(x), _clean(y))
    return {"r": float(r), "p_value": float(p), "is_significant": bool(p < 0.05)}


def spearman(x, y) -> dict:
    rho, p = stats.spearmanr(_clean(x), _clean(y))
    return {"rho": float(rho), "p_value": float(p), "is_significant": bool(p < 0.05)}


def cross_correlation(x, y, max_lag: int = 6) -> dict:
    """r_k for k in [-max_lag, +max_lag]; positive k = Y shifted forward vs X."""
    x, y = _clean(x), _clean(y)
    profile = []
    for k in range(-max_lag, max_lag + 1):
        if k >= 0:
            xs, ys = x[: len(x) - k or None], y[k:]
        else:
            xs, ys = x[-k:], y[: len(y) + k or None]
        r = float(stats.pearsonr(xs, ys)[0]) if len(xs) >= 3 else None
        profile.append({"lag": k, "r": r})
    valid = [p for p in profile if p["r"] is not None]
    best = max(valid, key=lambda p: abs(p["r"])) if valid else {"lag": 0, "r": None}
    return {"max_lag": max_lag, "profile": profile, "best_lag": best}


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

def cusum_change_point(years, values) -> dict:
    """CUSUM regime shift: year where cumulative anomalies peak + Welch t-test."""
    t, x = _clean(years), _clean(values)
    cusum = np.cumsum(x - x.mean())
    tau = int(np.argmax(np.abs(cusum)))
    pre, post = x[: tau + 1], x[tau + 1 :]
    p_val = None
    if len(pre) >= 2 and len(post) >= 2:
        p_val = float(stats.ttest_ind(pre, post, equal_var=False).pvalue)
    return {
        "breakpoint_index": tau,
        "breakpoint_year": int(t[tau]),
        "pre_mean": float(pre.mean()),
        "post_mean": float(post.mean()),
        "mean_shift": float(post.mean() - pre.mean()) if len(post) else 0.0,
        "welch_p_value": p_val,
        "is_significant": bool(p_val is not None and p_val < 0.05),
    }


def decade_comparison(years, values, window: int = 10) -> dict:
    t, x = _clean(years), _clean(values)
    w = min(window, len(x) // 2)
    first, last = x[:w], x[len(x) - w :]
    return {
        "window_years": w,
        "first_period": [int(t[0]), int(t[w - 1])],
        "last_period": [int(t[len(x) - w]), int(t[-1])],
        "first_mean": float(first.mean()),
        "last_mean": float(last.mean()),
        "delta": float(last.mean() - first.mean()),
    }


# ---------------------------------------------------------------------------
# Patterns & forecast
# ---------------------------------------------------------------------------

def fft_cycles(values, dt: float = 1.0, top: int = 3) -> dict:
    """Dominant cyclical periods (in units of dt) from an FFT of the
    detrended series."""
    x = _clean(values)
    n = len(x)
    if n < 6:
        return {"periods": [], "note": "series too short"}
    detrended = x - np.polyval(np.polyfit(np.arange(n), x, 1), np.arange(n))
    detrended = detrended * np.hanning(n)
    mag = np.abs(np.fft.rfft(detrended))
    freqs = np.fft.rfftfreq(n, d=dt)
    mag[0] = 0  # ignore DC
    order = np.argsort(mag)[::-1]
    periods, seen = [], set()
    for idx in order:
        if freqs[idx] <= 0:
            continue
        period = 1.0 / freqs[idx]
        key = round(period, 1)
        if key in seen or period > n:
            continue
        seen.add(key)
        periods.append({
            "period": float(period),
            "unit": "years" if dt == 1.0 else "samples",
            "magnitude": float(mag[idx]),
        })
        if len(periods) >= top:
            break
    return {"periods": periods}


def forecast(years, values, n_ahead: int = 10) -> dict:
    """Linear trend + AR(1) residual projection with 95 % prediction bands."""
    t, x = _clean(years), _clean(values)
    n = len(x)
    res = stats.linregress(t, x)
    fitted = res.intercept + res.slope * t
    resid = x - fitted
    phi = float(np.corrcoef(resid[:-1], resid[1:])[0, 1]) if n > 2 else 0.0
    phi = float(np.clip(phi, -0.95, 0.95))

    future_t = np.arange(int(t[-1]) + 1, int(t[-1]) + 1 + n_ahead)
    trend = res.intercept + res.slope * future_t
    residual_proj = resid[-1] * phi ** np.arange(1, n_ahead + 1)
    point = trend + residual_proj

    sigma = float(resid.std(ddof=2)) if n > 2 else float(resid.std())
    t_crit = float(stats.t.ppf(0.975, n - 2)) if n > 2 else 1.96
    sxx = float(((t - t.mean()) ** 2).sum())
    out = []
    for i, ft in enumerate(future_t):
        se = sigma * np.sqrt(1 + 1 / n + (ft - t.mean()) ** 2 / sxx)
        half = t_crit * se
        out.append({
            "year": int(ft),
            "prediction": float(point[i]),
            "lower95": float(point[i] - half),
            "upper95": float(point[i] + half),
        })
    return {
        "method": "linear_trend+AR(1)_residual",
        "ar1_phi": phi,
        "residual_std": sigma,
        "years_ahead": n_ahead,
        "forecast": out,
    }


# ---------------------------------------------------------------------------
# Multivariate summaries (NumPy only, no scikit-learn)
# ---------------------------------------------------------------------------

def pca_summary(matrix) -> dict:
    """2-component PCA via SVD on a (n_samples, n_features) matrix."""
    X = _clean(matrix)
    Xc = X - X.mean(axis=0)
    scale = Xc.std(axis=0)
    scale[scale == 0] = 1.0
    Xs = Xc / scale
    _, s, vt = np.linalg.svd(Xs, full_matrices=False)
    var = s**2 / max(len(Xs) - 1, 1)
    total = float(var.sum()) or 1.0
    return {
        "explained_variance_ratio": [float(v / total) for v in var[:2]],
        "components": vt[:2].tolist(),
        "scores": (Xs @ vt[:2].T).tolist(),
    }


def kmeans(matrix, k: int = 3, seed: int = 42, iters: int = 100) -> dict:
    """Lloyd's K-means with deterministic k-means++-ish init."""
    X = _clean(matrix)
    rng = np.random.default_rng(seed)
    centers = [X[rng.integers(len(X))]]
    for _ in range(k - 1):
        d = np.min(((X[:, None] - np.array(centers)[None]) ** 2).sum(-1), axis=1)
        centers.append(X[rng.choice(len(X), p=d / d.sum() if d.sum() else None)])
    centers = np.array(centers)
    labels = np.zeros(len(X), dtype=int)
    for _ in range(iters):
        d = ((X[:, None] - centers[None]) ** 2).sum(-1)
        new_labels = d.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for c in range(k):
            if np.any(labels == c):
                centers[c] = X[labels == c].mean(axis=0)
    return {"k": k, "labels": labels.tolist(), "centers": centers.tolist()}


# ---------------------------------------------------------------------------
# Detective verdict
# ---------------------------------------------------------------------------

def detective_verdict(
    *,
    place: str,
    variable_label: str,
    lang: str,
    linear: dict,
    mk: dict,
    sen: dict,
    cusum: dict,
    z: dict,
    decade: dict,
) -> str:
    """Human-readable interpretation of the analysis, ES default / EN toggle."""
    per_decade = sen["per_decade"]
    sign = "+" if per_decade >= 0 else ""
    if lang == "en":
        trend_txt = (
            f"a statistically significant {mk['direction']} trend"
            if mk["is_significant"]
            else "no statistically significant trend"
        )
        return (
            f"In {place}, {variable_label} shows {trend_txt} according to "
            f"Mann-Kendall (p={mk['p_value']:.3f}), with a Sen's slope of "
            f"{sign}{per_decade:.3f} per decade (linear R²={linear['r_squared']:.2f}). "
            f"A structural break is detected around {cusum['breakpoint_year']} "
            f"(pre mean {cusum['pre_mean']:.2f} → post mean {cusum['post_mean']:.2f}). "
            f"{z['n_outliers']} anomalous years (|Z|≥2) were flagged. The last "
            f"{decade['window_years']}-year mean differs from the first by "
            f"{decade['delta']:+.2f}."
        )
    trend_txt = (
        f"una tendencia {mk['direction']} estadísticamente significativa"
        if mk["is_significant"]
        else "una tendencia no significativa estadísticamente"
    )
    return (
        f"En {place}, la variable {variable_label} muestra {trend_txt} según "
        f"Mann-Kendall (p={mk['p_value']:.3f}) con una Pendiente de Sen de "
        f"{sign}{per_decade:.3f} por década (R² lineal={linear['r_squared']:.2f}). "
        f"Se detecta un punto de quiebre estructural hacia el año "
        f"{cusum['breakpoint_year']} (media {cusum['pre_mean']:.2f} → "
        f"{cusum['post_mean']:.2f}). Se marcaron {z['n_outliers']} años "
        f"anómalos (|Z|≥2). La media de los últimos "
        f"{decade['window_years']} años difiere de la primera en "
        f"{decade['delta']:+.2f}."
    )
