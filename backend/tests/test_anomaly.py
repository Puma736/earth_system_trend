import pytest

from app.stats.anomaly import anomalies, baseline, ranks


def test_baseline_needs_enough_years():
    assert baseline({y: 1.0 for y in range(2015, 2021)}, 1991, 2020) is None


def test_anomaly_z_and_percent_of_normal():
    record = {y: 10.0 + (1 if y % 2 else -1) for y in range(1991, 2021)}
    record[2024] = 6.0
    base = baseline(record, 1991, 2020)
    assert base.mean == pytest.approx(10.0)
    [a] = anomalies(record, [2024], base, -1)
    assert a.anomaly == pytest.approx(-4.0)
    assert a.z == pytest.approx(-4.0 / base.sd)
    assert a.percent_of_normal == pytest.approx(60.0)
    assert a.rank == 1  # el más bajo de todo el registro


def test_ranks_follow_the_extreme_direction_and_share_ties():
    record = {2001: 5.0, 2002: 9.0, 2003: 9.0, 2004: 1.0}
    assert ranks(record, +1) == {2002: 1, 2003: 1, 2001: 3, 2004: 4}
    assert ranks(record, -1)[2004] == 1


def test_flat_baseline_has_no_z():
    record = {y: 3.0 for y in range(1991, 2021)}
    [a] = anomalies(record, [2000], baseline(record, 1991, 2020), -1)
    assert a.z is None and a.anomaly == 0
