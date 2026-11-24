"""Feature engineering shared by the simulator, model training and prediction.

Using one function everywhere guarantees that the features seen at prediction
time are computed exactly like the ones the model was trained on.
"""

import pandas as pd

WEATHER_FEATURES = ["outdoor_temp_c", "humidity_pct", "cloud_cover_pct", "solar_radiation_w_m2"]
TIME_FEATURES = [
    "hour_of_day",
    "day_of_week",
    "month_num",
    "day_of_year",
    "is_weekend",
    "is_holiday",
    "is_peak_hour",
    "winter_flag",
    "spring_flag",
    "summer_flag",
    "fall_flag",
]
NUMERIC_FEATURES = WEATHER_FEATURES + TIME_FEATURES
CATEGORICAL_FEATURES = ["building"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

PEAK_HOURS = [7, 8, 9, 17, 18, 19, 20]


def holiday_mask(ts: pd.Series) -> pd.Series:
    """Holiday periods used by the simulator (end of year, 1 Jan, 4 Jul, late Nov, mid March)."""
    month, day = ts.dt.month, ts.dt.day
    return (
        ((month == 12) & day.between(24, 31))
        | ((month == 1) & (day == 1))
        | ((month == 7) & (day == 4))
        | ((month == 11) & day.between(22, 28))
        | ((month == 3) & day.between(15, 22))
    )


def add_time_features(df: pd.DataFrame, time_col: str = "time_ts") -> pd.DataFrame:
    """Add calendar features. day_of_week follows pandas: Monday = 0, Sunday = 6."""
    out = df.copy()
    ts = pd.to_datetime(out[time_col])
    month = ts.dt.month

    out["hour_of_day"] = ts.dt.hour
    out["day_of_week"] = ts.dt.dayofweek
    out["month_num"] = month
    out["day_of_year"] = ts.dt.dayofyear
    out["is_weekend"] = out["day_of_week"].isin([5, 6]).astype(int)
    out["is_holiday"] = holiday_mask(ts).astype(int)
    out["is_peak_hour"] = out["hour_of_day"].isin(PEAK_HOURS).astype(int)
    out["winter_flag"] = month.isin([12, 1, 2]).astype(int)
    out["spring_flag"] = month.isin([3, 4, 5]).astype(int)
    out["summer_flag"] = month.isin([6, 7, 8]).astype(int)
    out["fall_flag"] = month.isin([9, 10, 11]).astype(int)
    return out
