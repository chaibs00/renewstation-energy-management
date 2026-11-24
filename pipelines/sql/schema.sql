-- =============================================================================
-- RenewStation silver layer
-- Idempotent: safe to run several times (CREATE ... IF NOT EXISTS).
-- Used by `python -m renewstation init-db` and by the Postgres container on
-- first start (mounted in /docker-entrypoint-initdb.d).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Energy consumption: archive (full history), live (last 48 h), predicted (ML)
-- All three tables share the same columns.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS energy_consumption_hourly_archive (
    id                     VARCHAR(50) PRIMARY KEY,   -- YYYYMMDDHH_building
    time_ts                TIMESTAMP NOT NULL,
    building               VARCHAR(50) NOT NULL,

    -- Season flags
    winter_flag            SMALLINT NOT NULL,
    spring_flag            SMALLINT NOT NULL,
    summer_flag            SMALLINT NOT NULL,
    fall_flag              SMALLINT NOT NULL,

    -- Weather features
    outdoor_temp_c         NUMERIC(5,2),
    humidity_pct           NUMERIC(5,2),
    cloud_cover_pct        NUMERIC(5,2),
    solar_radiation_w_m2   NUMERIC(8,2),

    -- Time features (day_of_week: Monday = 0)
    hour_of_day            SMALLINT NOT NULL,
    day_of_week            SMALLINT NOT NULL,
    month_num              SMALLINT NOT NULL,
    day_of_year            SMALLINT NOT NULL,
    is_weekend             SMALLINT NOT NULL,
    is_holiday             SMALLINT NOT NULL,
    is_peak_hour           SMALLINT NOT NULL,

    -- Consumption breakdown (kW)
    lighting_kw            NUMERIC(10,4),
    hvac_kw                NUMERIC(10,4),
    special_equipment_kw   NUMERIC(10,4),
    use_kw                 NUMERIC(10,4),

    CONSTRAINT uk_archive_time_building UNIQUE (time_ts, building)
);
CREATE INDEX IF NOT EXISTS idx_archive_time     ON energy_consumption_hourly_archive(time_ts);
CREATE INDEX IF NOT EXISTS idx_archive_building ON energy_consumption_hourly_archive(building);

CREATE TABLE IF NOT EXISTS energy_consumption_hourly_live (
    LIKE energy_consumption_hourly_archive INCLUDING DEFAULTS INCLUDING CONSTRAINTS,
    PRIMARY KEY (id),
    CONSTRAINT uk_live_time_building UNIQUE (time_ts, building)
);
CREATE INDEX IF NOT EXISTS idx_live_time     ON energy_consumption_hourly_live(time_ts);
CREATE INDEX IF NOT EXISTS idx_live_building ON energy_consumption_hourly_live(building);

-- lighting / hvac / special equipment stay NULL: the model predicts use_kw only
CREATE TABLE IF NOT EXISTS predicted_energy_consumption_hourly (
    LIKE energy_consumption_hourly_archive INCLUDING DEFAULTS INCLUDING CONSTRAINTS,
    PRIMARY KEY (id),
    CONSTRAINT uk_pred_energy_time_building UNIQUE (time_ts, building)
);
CREATE INDEX IF NOT EXISTS idx_pred_energy_time     ON predicted_energy_consumption_hourly(time_ts);
CREATE INDEX IF NOT EXISTS idx_pred_energy_building ON predicted_energy_consumption_hourly(building);

-- -----------------------------------------------------------------------------
-- Weather: archive (observed) and forecast (next 7 days)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_archive_hourly (
    forecast_timestamp              TIMESTAMP PRIMARY KEY,
    forecast_date                   DATE NOT NULL,
    forecast_time                   TIME NOT NULL,
    temperature_c                   NUMERIC(5,2),
    humidity_pct                    NUMERIC(5,2),
    precipitation_mm                NUMERIC(6,2),
    precipitation_probability_pct   NUMERIC(5,2),
    weather_conditions              VARCHAR(100),
    wind_speed_kmh                  NUMERIC(6,2),
    wind_direction_deg              NUMERIC(5,2),
    pressure_hpa                    NUMERIC(7,2),
    cloud_cover_pct                 NUMERIC(5,2),
    solar_radiation_w_m2            NUMERIC(8,2),
    created_at                      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_weather_archive_date ON weather_archive_hourly(forecast_date);

CREATE TABLE IF NOT EXISTS weather_forecast_hourly (
    forecast_timestamp              TIMESTAMP PRIMARY KEY,
    forecast_date                   DATE NOT NULL,
    forecast_time                   TIME NOT NULL,
    temperature_c                   NUMERIC(5,2),
    humidity_pct                    NUMERIC(5,2),
    precipitation_mm                NUMERIC(6,2),
    precipitation_probability_pct   NUMERIC(5,2),
    weather_conditions              VARCHAR(100),
    wind_speed_kmh                  NUMERIC(6,2),
    wind_direction_deg              NUMERIC(5,2),
    pressure_hpa                    NUMERIC(7,2),
    cloud_cover_pct                 NUMERIC(5,2),
    solar_radiation_w_m2            NUMERIC(8,2)
);
CREATE INDEX IF NOT EXISTS idx_weather_forecast_date ON weather_forecast_hourly(forecast_date);

-- -----------------------------------------------------------------------------
-- Solar production: archive (kept for the API) and 7-day forecast
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solar_production_archive (
    id                     VARCHAR(50) PRIMARY KEY,
    timestamp              TIMESTAMP NOT NULL UNIQUE,
    temperature_c          NUMERIC(5,2),
    humidity_pct           NUMERIC(5,2),
    cloud_cover_pct        NUMERIC(5,2),
    solar_radiation_w_m2   NUMERIC(8,2),
    ghi_w_m2               NUMERIC(8,2),
    dni_w_m2               NUMERIC(8,2),
    dhi_w_m2               NUMERIC(8,2),
    cell_temperature_c     NUMERIC(5,2),
    dc_power_kw            NUMERIC(10,4),
    ac_power_kw            NUMERIC(10,4),
    real_production_kwh    NUMERIC(10,4),
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predicted_solar_production (
    timestamp                TIMESTAMPTZ PRIMARY KEY,
    temperature_c            DOUBLE PRECISION,
    humidity_pct             DOUBLE PRECISION,
    cloud_cover_pct          DOUBLE PRECISION,
    solar_radiation_w_m2     DOUBLE PRECISION,
    ghi_w_m2                 DOUBLE PRECISION,
    dni_w_m2                 DOUBLE PRECISION,
    dhi_w_m2                 DOUBLE PRECISION,
    cell_temperature_c       DOUBLE PRECISION,
    dc_power_kw              DOUBLE PRECISION,
    ac_power_kw              DOUBLE PRECISION,
    predicted_production_kwh DOUBLE PRECISION
);

-- -----------------------------------------------------------------------------
-- Batteries: real states (past) and predicted states (next 7 days)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS battery_state_real (
    id                     VARCHAR(50) UNIQUE,        -- YYYYMMDDHH_type
    timestamp              TIMESTAMP NOT NULL,
    battery_type           VARCHAR(20) NOT NULL CHECK (battery_type IN ('main', 'backup')),
    battery_capacity_kwh   NUMERIC(10,2) NOT NULL,
    solar_production_kwh   NUMERIC(10,4),
    consumption_kwh        NUMERIC(10,4),
    net_energy_kwh         NUMERIC(10,4),
    soc_start_pct          NUMERIC(5,2),
    soc_end_pct            NUMERIC(5,2),
    energy_stored_kwh      NUMERIC(10,2),
    battery_charge_kwh     NUMERIC(10,4),
    battery_discharge_kwh  NUMERIC(10,4),
    grid_import_kwh        NUMERIC(10,4),
    grid_export_kwh        NUMERIC(10,4),
    is_predicted           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (timestamp, battery_type)
);
CREATE INDEX IF NOT EXISTS idx_battery_real_ts ON battery_state_real(timestamp);

CREATE TABLE IF NOT EXISTS battery_state_predicted (
    LIKE battery_state_real INCLUDING DEFAULTS INCLUDING CONSTRAINTS,
    PRIMARY KEY (timestamp, battery_type),
    UNIQUE (id)
);
ALTER TABLE battery_state_predicted ALTER COLUMN is_predicted SET DEFAULT TRUE;
CREATE INDEX IF NOT EXISTS idx_battery_pred_ts ON battery_state_predicted(timestamp);

-- -----------------------------------------------------------------------------
-- Pipeline metadata (technical flags for the DAGs)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pipeline_metadata (
    key        VARCHAR(100) PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
