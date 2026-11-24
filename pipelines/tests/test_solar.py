import pandas as pd

from renewstation import config
from renewstation.simulation.solar import calculate_production


def _weather(hours, radiation, cloud=0.0, temp=25.0):
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime([f"2025-06-21 {h:02d}:00" for h in hours]),
            "temperature_c": temp,
            "cloud_cover_pct": cloud,
            "solar_radiation_w_m2": radiation,
        }
    )


def test_no_production_at_night():
    out = calculate_production(_weather([0, 3, 22], [0.0, 0.0, 0.0]))
    assert (out["predicted_production_kwh"] == 0).all()


def test_production_capped_at_peak_power():
    out = calculate_production(_weather([12], [5000.0], temp=0.0))
    assert out["ac_power_kw"].iloc[0] == config.PV_PEAK_POWER_KW


def test_noon_produces_more_than_morning():
    out = calculate_production(_weather([8, 12], [300.0, 900.0]))
    morning, noon = out["predicted_production_kwh"].tolist()
    assert 0 < morning < noon


def test_missing_daytime_radiation_uses_clear_sky_fallback():
    out = calculate_production(_weather([12], [0.0], cloud=50.0))
    assert out["ghi_w_m2"].iloc[0] == 950.0 * 0.5
