import pandas as pd

from renewstation.simulation.battery import BatteryConfig, simulate_series

CFG = BatteryConfig("main", capacity_kwh=100.0, max_charge_kw=30.0, max_discharge_kw=30.0)


def _series(consumption, solar):
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=len(consumption), freq=pd.Timedelta(hours=1)),
            "consumption_kwh": consumption,
            "solar_kwh": solar,
        }
    )


def test_state_of_charge_stays_between_0_and_100():
    df = _series([0, 0, 0, 0, 80, 80, 80, 80], [80, 80, 80, 80, 0, 0, 0, 0])
    out = simulate_series(df, CFG, start_energy_kwh=50.0)
    assert out["soc_end_pct"].between(0, 100).all()
    assert out["energy_stored_kwh"].between(0, CFG.capacity_kwh).all()


def test_energy_balance_every_hour():
    df = _series([10, 50, 5, 70], [40, 0, 60, 10])
    out = simulate_series(df, CFG, start_energy_kwh=20.0)
    supplied = out["solar_production_kwh"] + out["battery_discharge_kwh"] + out["grid_import_kwh"]
    used = out["consumption_kwh"] + out["battery_charge_kwh"] + out["grid_export_kwh"]
    assert ((supplied - used).abs() < 1e-9).all()


def test_charge_limited_by_power_and_surplus_exported():
    out = simulate_series(_series([0], [100]), CFG, start_energy_kwh=0.0)
    assert out["battery_charge_kwh"].iloc[0] == 30.0
    assert out["grid_export_kwh"].iloc[0] == 70.0


def test_empty_battery_imports_from_grid():
    out = simulate_series(_series([40], [0]), CFG, start_energy_kwh=0.0)
    assert out["battery_discharge_kwh"].iloc[0] == 0.0
    assert out["grid_import_kwh"].iloc[0] == 40.0
