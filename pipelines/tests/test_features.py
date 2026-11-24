import pandas as pd

from renewstation.forecasting.features import FEATURE_COLUMNS, add_time_features


def _features(timestamps):
    return add_time_features(pd.DataFrame({"time_ts": pd.to_datetime(timestamps)}))


def test_day_of_week_starts_on_monday():
    df = _features(["2025-11-17 10:00", "2025-11-23 10:00"])  # Monday, Sunday
    assert df["day_of_week"].tolist() == [0, 6]
    assert df["is_weekend"].tolist() == [0, 1]


def test_holidays_and_seasons():
    df = _features(["2025-12-25 12:00", "2025-07-04 12:00", "2025-05-10 12:00"])
    assert df["is_holiday"].tolist() == [1, 1, 0]
    assert df["winter_flag"].tolist() == [1, 0, 0]
    assert df["summer_flag"].tolist() == [0, 1, 0]
    assert df["spring_flag"].tolist() == [0, 0, 1]


def test_peak_hours():
    df = _features(["2025-01-01 08:00", "2025-01-01 13:00", "2025-01-01 19:00"])
    assert df["is_peak_hour"].tolist() == [1, 0, 1]


def test_feature_list_has_building_last():
    assert FEATURE_COLUMNS[-1] == "building"
    assert len(FEATURE_COLUMNS) == 16
