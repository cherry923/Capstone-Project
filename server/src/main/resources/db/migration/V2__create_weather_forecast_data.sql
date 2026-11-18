CREATE TABLE IF NOT EXISTS weather_forecast_raw_data (
    id                  BIGSERIAL PRIMARY KEY,
    source              VARCHAR(30)  NOT NULL,
    nx                  INTEGER      NOT NULL,
    ny                  INTEGER      NOT NULL,
    issued_at           TIMESTAMP    NOT NULL,
    forecast_time       TIMESTAMP    NOT NULL,
    category            VARCHAR(20)  NOT NULL,
    value_text          VARCHAR(100),
    value_numeric       DOUBLE PRECISION,
    unit                VARCHAR(30),
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_weather_forecast_raw_data
        UNIQUE (source, nx, ny, issued_at, forecast_time, category)
);

CREATE INDEX IF NOT EXISTS idx_weather_forecast_raw_lookup
    ON weather_forecast_raw_data (source, nx, ny, issued_at, forecast_time);

CREATE INDEX IF NOT EXISTS idx_weather_forecast_raw_target
    ON weather_forecast_raw_data (source, nx, ny, forecast_time);

CREATE TABLE IF NOT EXISTS weather_forecast_hourly_data (
    id                          BIGSERIAL PRIMARY KEY,
    source                      VARCHAR(30) NOT NULL,
    nx                          INTEGER     NOT NULL,
    ny                          INTEGER     NOT NULL,
    issued_at                   TIMESTAMP   NOT NULL,
    forecast_time               TIMESTAMP   NOT NULL,
    temperature                 DOUBLE PRECISION,
    humidity                    DOUBLE PRECISION,
    precipitation_probability   DOUBLE PRECISION,
    precipitation_type          DOUBLE PRECISION,
    precipitation_amount        DOUBLE PRECISION,
    snowfall_amount             DOUBLE PRECISION,
    sky                         DOUBLE PRECISION,
    wind_speed                  DOUBLE PRECISION,
    wind_direction              DOUBLE PRECISION,
    east_west_wind              DOUBLE PRECISION,
    north_south_wind            DOUBLE PRECISION,
    wave_height                 DOUBLE PRECISION,
    created_at                  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_weather_forecast_hourly_data
        UNIQUE (source, nx, ny, issued_at, forecast_time)
);

CREATE INDEX IF NOT EXISTS idx_weather_forecast_hourly_issue
    ON weather_forecast_hourly_data (source, nx, ny, issued_at, forecast_time);

CREATE INDEX IF NOT EXISTS idx_weather_forecast_hourly_target
    ON weather_forecast_hourly_data (source, nx, ny, forecast_time);
