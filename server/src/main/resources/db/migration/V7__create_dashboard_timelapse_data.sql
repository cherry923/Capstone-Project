CREATE TABLE IF NOT EXISTS dashboard_timelapse_period (
    id              BIGSERIAL PRIMARY KEY,
    period_key      VARCHAR(100) NOT NULL,
    label           VARCHAR(160) NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    description     TEXT,
    source          VARCHAR(120),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dashboard_timelapse_period_key UNIQUE (period_key)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_timelapse_period_active
    ON dashboard_timelapse_period (is_active, end_date DESC, created_at DESC);

CREATE TABLE IF NOT EXISTS dashboard_timelapse_station_frame (
    id                      BIGSERIAL PRIMARY KEY,
    period_id               BIGINT NOT NULL,
    frame_hour              INTEGER NOT NULL,
    station_id              VARCHAR(100) NOT NULL,
    station_name            VARCHAR(120) NOT NULL,
    region                  VARCHAR(120) NOT NULL,
    demand_kwh              DOUBLE PRECISION NOT NULL,
    pv_kw                   DOUBLE PRECISION NOT NULL,
    ess_percent             DOUBLE PRECISION NOT NULL,
    tariff_krw_per_kwh      DOUBLE PRECISION NOT NULL,
    share_energy_kwh        DOUBLE PRECISION NOT NULL DEFAULT 0,
    active_chargers         INTEGER,
    total_chargers          INTEGER,
    vehicle_count           INTEGER,
    status                  VARCHAR(30),
    command_text            TEXT,
    policy_text             TEXT,
    prediction_text         TEXT,
    CONSTRAINT fk_dashboard_timelapse_period
        FOREIGN KEY (period_id) REFERENCES dashboard_timelapse_period (id) ON DELETE CASCADE,
    CONSTRAINT uq_dashboard_timelapse_station_frame
        UNIQUE (period_id, frame_hour, station_id)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_timelapse_frame_period_hour
    ON dashboard_timelapse_station_frame (period_id, frame_hour);

CREATE INDEX IF NOT EXISTS idx_dashboard_timelapse_frame_station
    ON dashboard_timelapse_station_frame (station_id, frame_hour);
