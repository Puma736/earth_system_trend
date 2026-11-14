def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_regions(client):
    data = client.get("/api/regions").json()
    assert {r["id"] for r in data["regions"]} >= {"santa_cruz", "chiquitania"}
    assert {s["id"] for s in data["seasons"]} == {"ANN", "DRY", "FIRE"}


def test_unknown_region_is_404(client):
    assert client.get("/api/drought?region=mars").status_code == 404


def test_bad_years_are_422(client, fake_power):
    assert client.get("/api/drought?start=2020&end=2010").status_code == 422


def test_drought_dashboard(client, fake_power):
    resp = client.get("/api/drought?region=santa_cruz&season=DRY")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["indicators"]) == 6
    by_param = {i["param"]: i for i in data["indicators"]}
    assert by_param["T2M_MAX"]["points_to_drying"] is True
    assert by_param["PRECTOTCORR"]["verdict"] == "Real change"
    assert by_param["RH2M"]["verdict"] != "Real change"
    assert data["summary"]["pointing_to_drying"] == 5
    assert data["summary"]["text"].startswith("5 of 6 indicators point to drying")


def test_hotspots_without_csv_is_503(client, tmp_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        resp = client.get("/api/hotspots")
        assert resp.status_code == 503
        assert "download_firms" in resp.json()["detail"]
    finally:
        get_settings.cache_clear()


def test_hotspots_trend(client, firms_csv):
    data = client.get("/api/hotspots?season=FIRE").json()
    assert data["series"][0] == {"year": 2003, "value": 200}
    assert data["trend"]["slope_per_decade"] > 0
    assert data["verdict"] == "Real change"


def test_hotspot_grid(client, firms_csv):
    data = client.get("/api/hotspots/grid?year=2010&season=FIRE").json()
    assert data["cells"] == [{"lat": -17.75, "lon": -61.25, "count": 2 * 240}]  # agosto + septiembre


def test_link(client, fake_power, firms_csv):
    data = client.get("/api/link?season=FIRE&indicator=GWETTOP").json()
    assert data["n_years"] == 23
    # Suelo cada vez más seco y focos en aumento -> correlación negativa
    assert data["rho"] < -0.9
    assert data["caveat"] == "Relationship, not proof of cause."
