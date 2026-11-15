import os

import pytest

from app.data import firms, power
from app.data.errors import DataNotAvailable
from app.regions import BOLIVIA_BBOX, REGIONS, BBox


def test_parse_series_drops_annual_and_fill():
    out = power._parse_series({"202001": 1.0, "202002": -999, "202013": 5.0})
    assert out == {2020: {1: 1.0}}


def test_weighted_mean_uses_cos_latitude():
    cells = {(0.0, 0.0): {2020: {1: 10.0}}, (60.0, 0.0): {2020: {1: 0.0}}}
    # pesos 1 y 0,5 -> 10 * 1 / 1,5
    assert power.weighted_mean(cells)[2020][1] == pytest.approx(10 / 1.5)


def test_seasonal_series_requires_all_months():
    monthly = {2020: {6: 1.0, 7: 3.0}, 2021: {6: 1.0}}
    assert power.seasonal_series(monthly, (6, 7)) == {2020: 2.0}


def test_tiles_split_large_regions():
    tiles = power._tiles(BOLIVIA_BBOX)
    assert len(tiles) == 4
    for t in tiles:
        assert t.north - t.south <= 10 and t.east - t.west <= 10


def test_tiles_keep_small_regions_whole():
    bbox = REGIONS["santa-cruz"].bbox
    assert power._tiles(bbox) == [bbox]


def test_cell_center():
    assert firms.cell_center(-17.78) == -17.75
    assert firms.cell_center(-63.18) == -63.25


def test_yearly_counts_filters_region_and_months(firms_csv):
    counts = firms.yearly_counts(REGIONS["santa-cruz"].bbox, (8, 9), 2003, 2025)
    assert counts[2003] == 200
    assert counts[2010] == 2 * (100 + 20 * 7)  # la celda de 99999 queda fuera


def test_missing_csv_raises(tmp_path):
    with pytest.raises(DataNotAvailable):
        firms.load_cells(tmp_path / "nope.csv")


def test_load_cells_is_cached_until_the_file_changes(firms_csv):
    first = firms.load_cells(firms_csv)
    assert firms.load_cells(firms_csv) is first

    with firms_csv.open("a", newline="", encoding="utf-8") as fh:
        fh.write("2004,8,-17.75,-61.25,1\n")
    stat = firms_csv.stat()
    os.utime(firms_csv, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

    assert len(firms.load_cells(firms_csv)) == len(first) + 1


def test_bbox_contains():
    b = BBox(west=-10, south=-10, east=10, north=10)
    assert b.contains(0, 0) and not b.contains(11, 0)
