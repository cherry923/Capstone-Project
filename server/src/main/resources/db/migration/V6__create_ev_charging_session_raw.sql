-- KEPCO EV 충전 세션 raw 데이터 적재 테이블 (data.go.kr API 15102510 + enhanced)
-- 기존 ai_dispatch_* 테이블과 분리. 2020-2026 전 기간 + 시설구분 매핑 cover.

CREATE TABLE IF NOT EXISTS ev_charging_session_raw (
    id                      BIGSERIAL PRIMARY KEY,

    -- 출처 메타
    data_source             VARCHAR(20) NOT NULL,   -- 'api_v1' (2020-2022, 14col)
                                                    -- 'api_v2' (2024+, 19col)
                                                    -- 'enhanced' (시설구분 매핑 포함)
    uuid_period             VARCHAR(20),            -- '2020.06', '2020.12', '2021.06', etc

    -- 지역 (2024+ UUID와 enhanced에서 일부 활용)
    sido                    VARCHAR(50),            -- 시도 (NULL for 2020-2022 API)
    sigungu                 VARCHAR(50),            -- 시군구/구군

    -- KEPCO 조직
    headquarters            VARCHAR(50),            -- 본부
    business_office         VARCHAR(50),            -- 사업소

    -- 충전소
    station_id              VARCHAR(50),            -- 충전소ID / 충전소_아이디 (NULL for 2020-2022)
    station_name            VARCHAR(255),           -- 충전소명
    address                 TEXT,                   -- 주소

    -- 충전기
    charger_id              VARCHAR(50) NOT NULL,   -- 충전기ID / 충전기_아이디 (raw 식별자)
    charger_name            VARCHAR(50),            -- 충전기 / 충전기명 (예: "급속01", "완속02")
    charger_capacity_kw     INTEGER,                -- 충전용량 / 충전기용량 (kW)
    charger_method          VARCHAR(50),            -- 충전기방식 / 충전방식 (DC콤보, BC타입5핀 등) — 2024+
    charger_type            VARCHAR(20),            -- 충전기구분 / 충전구분 (급속/완속)

    -- 충전 세션
    charging_kwh            DOUBLE PRECISION NOT NULL,  -- 충전량 (kWh)
    duration_hours          INTEGER,                -- 충전시간 / 충전시간(시)
    duration_minutes        INTEGER,                -- 충전분 / 충전시간(분)
    end_date                DATE,                   -- 충전종료일자 / 충전종료일
    start_time              TIMESTAMP NOT NULL,     -- 충전시작시각
    end_time                TIMESTAMP,              -- 충전종료시각

    -- 용도/시설 분류
    usage_category          VARCHAR(50),            -- "용도" (공용/아파트용/업무용) - 2024+ API
    facility_main           VARCHAR(50),            -- "시설구분(대)" - enhanced 전용 (10종)
    facility_sub            VARCHAR(50),            -- "시설구분(소)" - enhanced 전용 (50종)

    -- 정규화 키 (enhanced 또는 우리가 별도 가공)
    key_station_name        VARCHAR(255),
    key_address             TEXT,

    -- 적재 메타
    fetched_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_ev_charging_session
        UNIQUE (charger_id, start_time, data_source)
);

CREATE INDEX IF NOT EXISTS idx_ev_charging_session_start
    ON ev_charging_session_raw (start_time);

CREATE INDEX IF NOT EXISTS idx_ev_charging_session_charger
    ON ev_charging_session_raw (charger_id, start_time);

CREATE INDEX IF NOT EXISTS idx_ev_charging_session_station
    ON ev_charging_session_raw (station_id);

CREATE INDEX IF NOT EXISTS idx_ev_charging_session_period
    ON ev_charging_session_raw (data_source, uuid_period);

CREATE INDEX IF NOT EXISTS idx_ev_charging_session_facility
    ON ev_charging_session_raw (facility_main, facility_sub);

CREATE INDEX IF NOT EXISTS idx_ev_charging_session_sido
    ON ev_charging_session_raw (sido, sigungu);

COMMENT ON TABLE ev_charging_session_raw IS
    'KEPCO EV 충전 세션 raw 데이터 (data.go.kr API 15102510 + 시설구분 enhanced). 기존 ai_dispatch_* 테이블과 별도.';
COMMENT ON COLUMN ev_charging_session_raw.data_source IS
    'api_v1: 2020-2022 API (14컬럼), api_v2: 2024+ API (19컬럼), enhanced: KEPCO 시설구분 매핑 추가본';
