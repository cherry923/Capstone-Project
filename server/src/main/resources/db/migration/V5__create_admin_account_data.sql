CREATE TABLE IF NOT EXISTS admin_account (
    id              BIGSERIAL PRIMARY KEY,
    username        VARCHAR(60)  NOT NULL,
    password_hash   VARCHAR(100) NOT NULL,
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_admin_account_username UNIQUE (username)
);

CREATE TABLE IF NOT EXISTS admin_charging_station (
    id              BIGSERIAL PRIMARY KEY,
    admin_id        BIGINT       NOT NULL,
    station_id      VARCHAR(100) NOT NULL,
    station_name    VARCHAR(120) NOT NULL,
    region          VARCHAR(120) NOT NULL,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    status          VARCHAR(30)  NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_admin_charging_station_admin
        FOREIGN KEY (admin_id) REFERENCES admin_account (id) ON DELETE CASCADE,
    CONSTRAINT uq_admin_charging_station
        UNIQUE (admin_id, station_id)
);

CREATE INDEX IF NOT EXISTS idx_admin_charging_station_admin
    ON admin_charging_station (admin_id);

CREATE INDEX IF NOT EXISTS idx_admin_charging_station_station
    ON admin_charging_station (station_id);
