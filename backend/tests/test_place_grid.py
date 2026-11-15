from app.data.place_grid import bin_points, geometry_contains, snap_center

SQUARE = {
    "type": "Feature",
    "properties": {"id": "box", "name": "Box"},
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
    },
}


def test_snap_center_works_for_west_longitudes():
    assert snap_center(-63.2, 0.05) == -63.175
    assert snap_center(0.2, 0.05) == 0.225


def test_square_contains_its_interior_only():
    geometry = SQUARE["geometry"]
    assert geometry_contains(geometry, 0.5, 0.5)
    assert not geometry_contains(geometry, -0.1, 0.5)


def test_bin_points_keeps_cells_whose_center_is_inside():
    inside = bin_points([(0.22, 0.22)], [SQUARE])
    assert inside == [{"lat": 0.225, "lon": 0.225, "count": 1}]
    assert bin_points([(-0.1, 0.22)], [SQUARE]) == []
