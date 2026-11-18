#!/usr/bin/env python3
"""
Load KPX regional hourly solar generation into pv_actual_hourly_data.

The KPX CSV uses trade hours 1..24. This loader stores hour 1 as 00:00 of the
trade date and hour 24 as 23:00 of the trade date.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlparse

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_PATHS = (
    PROJECT_ROOT / ".env",
    PROJECT_ROOT / "server" / ".env",
)
DEFAULT_SOURCE = "KPX_REGIONAL_HOURLY_SOLAR_WIND"
DEFAULT_FUEL = "태양광"
DEFAULT_CSV_PATTERNS = (
    "artifacts/received_models/2026-05-06/han_pv_data/*지역별*시간별*태양광*풍력*발전량*.csv",
    "artifacts/kakaotalk_capstone_ai_analysis/*지역별*시간별*태양광*풍력*발전량*.csv",
)


@dataclass(frozen=True)
class DbConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str


def load_env_files() -> None:
    for path in ENV_PATHS:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_jdbc_url(raw: str) -> dict[str, str]:
    if not raw.startswith("jdbc:postgresql://"):
        return {}
    parsed = urlparse(raw.removeprefix("jdbc:"))
    database = parsed.path.lstrip("/")
    params = dict(parse_qsl(parsed.query))
    return {
        "host": parsed.hostname or "",
        "port": str(parsed.port or 5432),
        "dbname": database,
        **params,
    }


def db_config_from_env() -> DbConfig:
    jdbc = parse_jdbc_url(os.getenv("DB_URL", ""))
    host = os.getenv("DB_HOST") or jdbc.get("host")
    port = os.getenv("DB_PORT") or jdbc.get("port") or "5432"
    dbname = os.getenv("DB_NAME") or jdbc.get("dbname")
    user = os.getenv("DB_USERNAME") or jdbc.get("user")
    password = os.getenv("DB_PASSWORD") or jdbc.get("password")
    missing = [
        name
        for name, value in {
            "DB_HOST or DB_URL": host,
            "DB_NAME or DB_URL": dbname,
            "DB_USERNAME": user,
            "DB_PASSWORD": password,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing DB settings: {', '.join(missing)}")
    return DbConfig(
        host=str(host),
        port=int(port),
        dbname=str(dbname),
        user=str(user),
        password=str(password),
    )


def find_default_csv() -> Path:
    matches: list[Path] = []
    for pattern in DEFAULT_CSV_PATTERNS:
        matches.extend(PROJECT_ROOT.glob(pattern))
    unique = sorted({path.resolve() for path in matches})
    if not unique:
        raise FileNotFoundError("KPX PV CSV was not found. Pass --csv explicitly.")
    return unique[0]


def read_csv_auto(path: Path) -> pd.DataFrame:
    errors: list[str] = []
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
    raise UnicodeDecodeError("csv", b"", 0, 1, "; ".join(errors))


def first_existing_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    raise ValueError(f"Missing required column. Tried: {', '.join(candidates)}")


def normalize_frame(
    frame: pd.DataFrame,
    source: str,
    fuel: str,
    regions: set[str] | None,
) -> pd.DataFrame:
    date_col = first_existing_column(frame, ("거래일", "거래일자"))
    hour_col = first_existing_column(frame, ("거래시간", "시간"))
    region_col = first_existing_column(frame, ("지역", "지역명"))
    fuel_col = first_existing_column(frame, ("연료원", "발전원"))
    generation_col = first_existing_column(frame, ("전력거래량(MWh)", "발전량", "태양광 발전량"))

    work = frame[[date_col, hour_col, region_col, fuel_col, generation_col]].copy()
    work.columns = ["trade_date", "trade_hour", "region", "fuel_type", "generation_mwh"]
    work["region"] = work["region"].astype(str).str.strip()
    work["fuel_type"] = work["fuel_type"].astype(str).str.strip()
    work = work[work["fuel_type"] == fuel].copy()
    if regions:
        work = work[work["region"].isin(regions)].copy()

    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="raise").dt.date
    work["trade_hour"] = pd.to_numeric(work["trade_hour"], errors="raise").astype(int)
    invalid_hours = work[~work["trade_hour"].between(1, 24)]
    if not invalid_hours.empty:
        raise ValueError(f"Invalid trade_hour rows: {len(invalid_hours)}")

    work["generation_mwh"] = (
        work["generation_mwh"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .pipe(pd.to_numeric, errors="raise")
        .clip(lower=0.0)
    )
    work["observed_at"] = pd.to_datetime(work["trade_date"].astype(str)) + pd.to_timedelta(
        work["trade_hour"] - 1,
        unit="h",
    )
    work["source"] = source
    return work[
        ["source", "region", "fuel_type", "observed_at", "trade_date", "trade_hour", "generation_mwh"]
    ].sort_values(["region", "observed_at"])


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
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
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_pv_actual_hourly_lookup
                ON pv_actual_hourly_data (source, region, fuel_type, observed_at)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_pv_actual_hourly_region_date
                ON pv_actual_hourly_data (region, fuel_type, trade_date)
            """
        )
    conn.commit()


def upsert_rows(conn, frame: pd.DataFrame, batch_size: int) -> int:
    rows = [
        (
            row.source,
            row.region,
            row.fuel_type,
            row.observed_at.to_pydatetime(),
            row.trade_date,
            int(row.trade_hour),
            float(row.generation_mwh),
        )
        for row in frame.itertuples(index=False)
    ]
    if not rows:
        return 0

    sql = """
        INSERT INTO pv_actual_hourly_data (
            source, region, fuel_type, observed_at, trade_date, trade_hour, generation_mwh
        )
        VALUES %s
        ON CONFLICT (source, region, fuel_type, observed_at)
        DO UPDATE SET
            trade_date = EXCLUDED.trade_date,
            trade_hour = EXCLUDED.trade_hour,
            generation_mwh = EXCLUDED.generation_mwh,
            updated_at = CURRENT_TIMESTAMP
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=batch_size)
    conn.commit()
    return len(rows)


def print_summary(frame: pd.DataFrame) -> None:
    if frame.empty:
        print("No rows selected.")
        return
    summary = (
        frame.groupby(["region", "fuel_type"], as_index=False)
        .agg(
            rows=("generation_mwh", "size"),
            start=("observed_at", "min"),
            end=("observed_at", "max"),
            total_mwh=("generation_mwh", "sum"),
        )
        .sort_values(["region", "fuel_type"])
    )
    print(summary.to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=None, help="KPX CSV path")
    parser.add_argument("--region", action="append", help="Region to load. Repeatable. Default: all")
    parser.add_argument("--fuel", default=DEFAULT_FUEL, help="Fuel type to load")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Source label")
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env_files()

    csv_path = (args.csv or find_default_csv()).resolve()
    raw = read_csv_auto(csv_path)
    regions = {item.strip() for item in args.region} if args.region else None
    frame = normalize_frame(raw, args.source, args.fuel, regions)

    print(f"CSV: {csv_path}")
    print_summary(frame)

    if args.dry_run:
        return

    config = db_config_from_env()
    with psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
        connect_timeout=15,
    ) as conn:
        ensure_table(conn)
        count = upsert_rows(conn, frame, args.batch_size)
    print(f"Upserted rows: {count}")


if __name__ == "__main__":
    main()
