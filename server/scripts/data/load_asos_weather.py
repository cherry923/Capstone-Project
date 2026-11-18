#!/usr/bin/env python3
"""
Load hourly ASOS observations into weather_raw_data.

The data.go.kr ASOS endpoint limits each request to 1,000 rows, so this loader
queries one calendar month at a time and upserts rows by (asos_station_id,
observation_time).
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse
from urllib.request import urlopen

import psycopg2
from psycopg2.extras import execute_values


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_PATHS = (
    PROJECT_ROOT / ".env",
    PROJECT_ROOT / "server" / ".env",
)
DEFAULT_BASE_URL = "https://apis.data.go.kr/1360000/AsosHourlyInfoService"


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
    return DbConfig(str(host), int(port), str(dbname), str(user), str(password))


def connect():
    config = db_config_from_env()
    return psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
        connect_timeout=15,
    )


def request_windows(start: date, end_exclusive: date) -> list[tuple[date, date]]:
    windows: list[tuple[date, date]] = []
    current = start
    while current < end_exclusive:
        window_end = min(current + timedelta(days=20), end_exclusive)
        windows.append((current, window_end))
        current = window_end
    return windows


def request_month(station_id: int, start: date, end_exclusive: date, service_key: str, base_url: str) -> list[dict[str, Any]]:
    end_inclusive = end_exclusive - timedelta(days=1)
    params = {
        "ServiceKey": service_key,
        "dataType": "JSON",
        "dataCd": "ASOS",
        "dateCd": "HR",
        "startDt": start.strftime("%Y%m%d"),
        "startHh": "00",
        "endDt": end_inclusive.strftime("%Y%m%d"),
        "endHh": "23",
        "stnIds": str(station_id),
        "numOfRows": "999",
        "pageNo": "1",
    }
    url = f"{base_url.rstrip('/')}/getWthrDataList?{urlencode(params)}"
    with urlopen(url, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    response = payload.get("response") or {}
    header = response.get("header") or {}
    if header.get("resultCode") != "00":
        raise RuntimeError(f"ASOS API error station={station_id}, start={start}: {header}")
    body = response.get("body") or {}
    items = (body.get("items") or {}).get("item") or []
    total_count = int(body.get("totalCount") or 0)
    if total_count > len(items):
        raise RuntimeError(
            f"ASOS response truncated station={station_id}, start={start}, total={total_count}, items={len(items)}"
        )
    return items


def parse_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def to_row(item: dict[str, Any], fallback_station_id: int) -> tuple[Any, ...]:
    observed_at = datetime.strptime(item["tm"], "%Y-%m-%d %H:%M")
    return (
        int(item.get("stnId") or fallback_station_id),
        observed_at,
        item.get("stnNm"),
        parse_float(item.get("ta")),
        parse_float(item.get("rn")),
        parse_float(item.get("hm")),
        parse_float(item.get("dsnw")),
        parse_float(item.get("dc10Tca")),
        parse_float(item.get("ss")),
        parse_float(item.get("icsr")),
        parse_float(item.get("ws")),
        parse_int(item.get("wd")),
    )


def upsert_rows(conn, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    query = """
        INSERT INTO weather_raw_data (
            asos_station_id,
            observation_time,
            station_name,
            temperature,
            rainfall,
            humidity,
            snowfall,
            cloud_cover,
            sunshine_duration,
            solar_radiation,
            wind_speed,
            wind_direction
        )
        VALUES %s
        ON CONFLICT (asos_station_id, observation_time) DO UPDATE SET
            station_name = EXCLUDED.station_name,
            temperature = EXCLUDED.temperature,
            rainfall = EXCLUDED.rainfall,
            humidity = EXCLUDED.humidity,
            snowfall = EXCLUDED.snowfall,
            cloud_cover = EXCLUDED.cloud_cover,
            sunshine_duration = EXCLUDED.sunshine_duration,
            solar_radiation = EXCLUDED.solar_radiation,
            wind_speed = EXCLUDED.wind_speed,
            wind_direction = EXCLUDED.wind_direction
    """
    execute_values(conn.cursor(), query, rows, page_size=1000)


def load_station(station_id: int, start: date, end_exclusive: date, service_key: str, base_url: str) -> int:
    total = 0
    with connect() as conn:
        for window_start, window_end in request_windows(start, end_exclusive):
            items = request_month(station_id, window_start, window_end, service_key, base_url)
            rows = [to_row(item, station_id) for item in items]
            upsert_rows(conn, rows)
            conn.commit()
            total += len(rows)
            print(
                f"station={station_id} {window_start}..{window_end - timedelta(days=1)} rows={len(rows)} total={total}",
                flush=True,
            )
    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stations", nargs="+", type=int, required=True)
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default="2026-01-01", help="exclusive end date")
    parser.add_argument("--base-url", default=os.getenv("ASOS_BASE_URL", DEFAULT_BASE_URL))
    return parser.parse_args()


def main() -> None:
    load_env_files()
    args = parse_args()
    service_key = os.getenv("ASOS_SERVICE_KEY")
    if not service_key:
        raise RuntimeError("ASOS_SERVICE_KEY is required")
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    for station_id in args.stations:
        total = load_station(station_id, start, end, service_key, args.base_url)
        print(f"saved station={station_id} rows={total}")


if __name__ == "__main__":
    main()
