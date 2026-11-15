import numpy as np
import pytest

from app.stats.trend import fdr, spearman, trend


def test_trend_detects_clear_increase():
    years = list(range(1981, 2026))
    rng = np.random.default_rng(0)
    values = [0.5 * (y - 1981) + rng.normal(0, 1) for y in years]
    t = trend(years, values)
    assert t.slope_per_decade == pytest.approx(5, rel=0.2)
    assert t.p_value < 0.05
    assert t.direction == 1


def test_sen_range_and_total_change():
    years = list(range(1981, 2026))
    rng = np.random.default_rng(3)
    t = trend(years, [0.1 * (y - 1981) + rng.normal(0, 0.5) for y in years])
    assert t.slope_low_per_decade < t.slope_per_decade < t.slope_high_per_decade
    assert t.slope_low_per_decade > 0  # el rango no toca el cero
    assert t.total_change == pytest.approx(t.slope_per_decade / 10 * 44)
    assert t.notes == ()


def test_linear_regression_control_agrees_on_clean_trend():
    years = list(range(2000, 2030))
    t = trend(years, [3.0 - 0.2 * (y - 2000) for y in years])
    assert t.ols_slope_per_decade == pytest.approx(-2.0)
    assert t.ols_p_value < 0.05


def test_note_when_one_extreme_year_drives_regression():
    # Serie que baja casi siempre, pero los últimos años gigantes tiran la regresión hacia arriba.
    years = list(range(1990, 2020))
    values = [10.0 - 0.05 * (y - 1990) for y in years]
    values[-4:] = [200.0] * 4
    t = trend(years, values)
    assert t.direction == -1
    assert t.ols_slope_per_decade > 0
    assert any("Linear regression" in n for n in t.notes)


def test_note_when_short_series_has_strong_memory():
    # 20 años de ruido AR(1) muy persistente: si sale "significativo", tiene que avisar.
    rng = np.random.default_rng(5)
    years = list(range(2003, 2023))
    noted = 0
    for _ in range(200):
        values = np.zeros(len(years))
        for i in range(1, len(years)):
            values[i] = 0.9 * values[i - 1] + rng.normal()
        t = trend(years, list(values))
        if t.p_value < 0.05:
            noted += any("strongly linked" in n for n in t.notes)
    assert noted > 0


def test_no_memory_note_on_long_or_independent_series():
    rng = np.random.default_rng(1)
    years = list(range(1981, 2026))
    t = trend(years, [0.3 * (y - 1981) + rng.normal() for y in years])
    assert not any("strongly linked" in n for n in t.notes)


def test_trend_on_noise_is_not_significant():
    years = list(range(1981, 2026))
    # Con ruido puro, a lo sumo ~5% de las series deberían salir "significativas".
    rng = np.random.default_rng(42)
    false_positives = sum(
        trend(years, list(rng.normal(0, 1, len(years)))).p_value < 0.05 for _ in range(200)
    )
    assert false_positives <= 20


def test_constant_series_is_not_significant():
    t = trend(list(range(2000, 2020)), [0.0] * 20)
    assert t.p_value == 1.0 and t.slope_per_decade == 0


def test_trend_needs_enough_years():
    with pytest.raises(ValueError):
        trend([2000, 2001, 2002], [1, 2, 3])


def test_trend_tolerates_missing_year():
    years = [y for y in range(1990, 2020) if y != 2005]
    t = trend(years, [2.0 * (y - 1990) for y in years])
    assert t.slope_per_decade == pytest.approx(20)
    assert t.intercept == pytest.approx(0)


def test_fdr_is_never_smaller_than_p():
    p = [0.01, 0.04, 0.03, 0.5]
    q = fdr(p)
    assert all(qi >= pi for pi, qi in zip(p, q))


def test_spearman_perfect_negative():
    r = spearman([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
    assert r.rho == pytest.approx(-1)


def test_pettitt_finds_a_step():
    from app.stats.changepoint import pettitt

    rng = np.random.default_rng(2)
    years = list(range(1990, 2020))
    values = [rng.normal(0, 1) + (3 if y >= 2005 else 0) for y in years]
    cp = pettitt(years, values)
    assert cp.year == 2005 and cp.p_value < 0.01
    assert cp.mean_after > cp.mean_before


def test_pettitt_on_noise_is_rarely_significant():
    from app.stats.changepoint import pettitt

    rng = np.random.default_rng(9)
    years = list(range(1981, 2026))
    hits = sum(pettitt(years, list(rng.normal(0, 1, 45))).p_value < 0.05 for _ in range(200))
    assert hits <= 20  # ~5 % esperado; la aproximación es conservadora
