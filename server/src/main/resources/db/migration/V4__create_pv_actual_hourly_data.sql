CREATE TABLE IF NOT EXISTS pv_actual_hourly_data (
    id                  BIGSERIAL PRIMARY KEY,
    source              VARCHAR(60)      NOT NULL,
    region              VARCHAR(50)      NOT NULL,
    fuel_type           VARCHAR(30)      NOT NULL,
    observed_at         TIMESTAMP        NOT NULL,
    trade_date          DATE             NOT NULL,
    trade_hour          INTEGER          NOT NULL,
    generation_mwh      DOUBLE PRECISION NOT NULL,
    created_at          TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pv_actual_hourly_data
        UNIQUE (source, region, fuel_type, observed_at),
    CONSTRAINT chk_pv_actual_trade_hour
        CHECK (trade_hour BETWEEN 1 AND 24),
    CONSTRAINT chk_pv_actual_generation_non_negative
        CHECK (generation_mwh >= 0)
);

CREATE INDEX IF NOT EXISTS idx_pv_actual_hourly_lookup
    ON pv_actual_hourly_data (source, region, fuel_type, observed_at);

CREATE INDEX IF NOT EXISTS idx_pv_actual_hourly_region_date
    ON pv_actual_hourly_data (region, fuel_type, trade_date);
