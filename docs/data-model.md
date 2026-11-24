# Data model (silver layer)

Full definitions: [`pipelines/sql/schema.sql`](../pipelines/sql/schema.sql).

| Table | Content | Written by |
|---|---|---|
| `weather_archive_hourly` | Observed hourly weather since 2024-01-01 | `ingest-weather`, `archive-yesterday` |
| `weather_forecast_hourly` | Hourly forecast for the next 7 days | `ingest-weather` |
| `energy_consumption_hourly_archive` | Simulated consumption of the 17 buildings, full history | `simulate-energy`, `archive-yesterday` |
| `energy_consumption_hourly_live` | Same, last 48 hours only | `simulate-energy` |
| `predicted_energy_consumption_hourly` | ML forecast per building, next 7 days | `predict-energy` |
| `predicted_solar_production` | PV production forecast, next 7 days | `predict-solar` |
| `solar_production_archive` | Kept for the API, not filled by the pipelines | - |
| `battery_state_real` | Hourly battery states (main + backup), past days | `init-batteries`, `battery-real` |
| `battery_state_predicted` | Hourly battery states, next 7 days | `predict-battery` |
| `pipeline_metadata` | Technical flags (initialization done) | `mark-initialized` |

## Keys

- Energy tables: `id = YYYYMMDDHH_building`, unique on `(time_ts, building)`.
- Weather tables: primary key `forecast_timestamp`.
- Battery tables: primary key `(timestamp, battery_type)`, `id = YYYYMMDDHH_type`.

## Model features

Stored with every consumption row, and computed by `forecasting/features.py`:

| Group | Columns |
|---|---|
| Weather | `outdoor_temp_c`, `humidity_pct`, `cloud_cover_pct`, `solar_radiation_w_m2` |
| Time | `hour_of_day`, `day_of_week` (Monday = 0), `month_num`, `day_of_year`, `is_weekend`, `is_holiday`, `is_peak_hour` |
| Season | `winter_flag`, `spring_flag`, `summer_flag`, `fall_flag` |
| Building | `building` |
| Target | `use_kw` |
