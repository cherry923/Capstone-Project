CREATE TABLE IF NOT EXISTS ai_dispatch_run (
    id                  BIGSERIAL PRIMARY KEY,
    request_id          VARCHAR(100),
    target_date         DATE,
    status              VARCHAR(50) NOT NULL,
    message             TEXT,
    model_version       VARCHAR(100),
    model_name          VARCHAR(200),
    model_status        VARCHAR(100),
    pv_source           VARCHAR(100),
    ev_source           TEXT,
    team_model_source   TEXT,
    command_count       INTEGER,
    request_payload     TEXT NOT NULL,
    response_payload    TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_dispatch_run_request
    ON ai_dispatch_run (request_id);

CREATE INDEX IF NOT EXISTS idx_ai_dispatch_run_target_date
    ON ai_dispatch_run (target_date);

CREATE INDEX IF NOT EXISTS idx_ai_dispatch_run_created_at
    ON ai_dispatch_run (created_at);

CREATE TABLE IF NOT EXISTS ai_dispatch_command (
    id                  BIGSERIAL PRIMARY KEY,
    dispatch_run_id     BIGINT NOT NULL,
    command_index       INTEGER NOT NULL,
    dispatch_hour       INTEGER,
    station_id          VARCHAR(100),
    share_energy_kwh    DOUBLE PRECISION,
    ess_action          DOUBLE PRECISION,
    raw_ess_action      DOUBLE PRECISION,
    pv_priority         DOUBLE PRECISION,
    soc_before          DOUBLE PRECISION,
    soc_after           DOUBLE PRECISION,
    grid_total_kwh      DOUBLE PRECISION,
    grid_cost           DOUBLE PRECISION,
    command             VARCHAR(100),
    safety_adjusted     BOOLEAN,
    command_payload     TEXT NOT NULL,
    CONSTRAINT fk_ai_dispatch_command_run
        FOREIGN KEY (dispatch_run_id) REFERENCES ai_dispatch_run (id) ON DELETE CASCADE,
    CONSTRAINT uq_ai_dispatch_command
        UNIQUE (dispatch_run_id, command_index)
);

CREATE INDEX IF NOT EXISTS idx_ai_dispatch_command_run
    ON ai_dispatch_command (dispatch_run_id);

CREATE INDEX IF NOT EXISTS idx_ai_dispatch_command_station_hour
    ON ai_dispatch_command (station_id, dispatch_hour);
