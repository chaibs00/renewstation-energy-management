import pandas as pd

from renewstation.simulation.buildings import building_names, buildings
from renewstation.simulation.energy import simulate_building, simulate_district


def _weather(days=2):
    ts = pd.date_range("2025-01-06", periods=24 * days, freq=pd.Timedelta(hours=1))
    return pd.DataFrame(
        {
            "time_ts": ts,
            "outdoor_temp_c": 12.0,
            "humidity_pct": 70.0,
            "cloud_cover_pct": 20.0,
            "solar_radiation_w_m2": [max(0.0, 600 - abs(h - 12) * 100) for h in ts.hour],
        }
    )


def test_district_has_17_buildings():
    assert len(buildings()) == 17
    assert building_names()[:2] == ["Hospital", "House1"]
    assert building_names()[-1] == "School"


def test_simulation_is_reproducible_and_positive():
    building = buildings()[1]
    first = simulate_building(_weather(), building)
    second = simulate_building(_weather(), building)
    assert first["use_kw"].equals(second["use_kw"])
    assert (first["use_kw"] >= 0).all()


def test_district_output_shape():
    out = simulate_district(_weather(days=1))
    assert len(out) == 24 * 17
    assert {"use_kw", "lighting_kw", "hvac_kw", "special_equipment_kw", "building"} <= set(out.columns)
