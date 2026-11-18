CREATE TABLE IF NOT EXISTS weather_raw_data (
    id                  BIGSERIAL PRIMARY KEY,
    asos_station_id     INTEGER       NOT NULL,
    observation_time    TIMESTAMP     NOT NULL,
    station_name        VARCHAR(50),
    temperature         DOUBLE PRECISION,
    rainfall            DOUBLE PRECISION,
    humidity            DOUBLE PRECISION,
    snowfall            DOUBLE PRECISION,
    cloud_cover         DOUBLE PRECISION,
    sunshine_duration   DOUBLE PRECISION,
    solar_radiation     DOUBLE PRECISION,
    wind_speed          DOUBLE PRECISION,
    wind_direction      INTEGER,
    CONSTRAINT uq_station_time UNIQUE (asos_station_id, observation_time)
);

CREATE INDEX idx_weather_station_time
    ON weather_raw_data (asos_station_id, observation_time);
