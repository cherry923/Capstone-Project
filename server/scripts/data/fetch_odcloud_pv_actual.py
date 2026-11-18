#!/usr/bin/env python3
"""
Fetch odcloud-converted KPX PV actual data and normalize it for the RDS loader.

Output columns are compatible with load_kpx_pv_actual.py:
거래일, 거래시간, 지역, 연료원, 전력거래량(MWh)
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse
from urllib.request import Request, urlopen

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_PATHS = (
    PROJECT_ROOT / ".env",
    PROJECT_ROOT / "server" / ".env",
)
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "processed" / "pv" / "odcloud_20260519"
MINUTE_COLUMNS = [
    "0분",
    "5분",
    "10분",
    "15분",
    "20분",
    "25분",
    "30분",
    "35분",
    "40분",
    "45분",
    "50분",
    "55분",
]
CORRUPT_5MIN_WH_THRESHOLD = 1_000_000_000.0


@dataclass(frozen=True)
class Endpoint:
    label: str
    url: str
    dataset: str
    remote_date_col: str


ENDPOINTS = {
    "metered_20241031": Endpoint(
        label="metered_20241031",
        dataset="metered_5min",
        remote_date_col="거래일",
        url="https://api.odcloud.kr/api/15065240/v1/uddi:3fcf3997-7946-4ebd-9a61-cd72c660a961",
    ),
    "metered_20251231": Endpoint(
        label="metered_20251231",
        dataset="metered_5min",
        remote_date_col="거래일",
        url="https://api.odcloud.kr/api/15065240/v1/uddi:72d12f6b-96f7-4aaa-a49a-f9b9ef9110bd",
    ),
    "trading_20230228": Endpoint(
        label="trading_20230228",
        dataset="trading_hourly",
        remote_date_col="거래일자",
        url="https://api.odcloud.kr/api/15065269/v1/uddi:166a7ee3-161a-4dc2-9f59-cedb6b1c7213",
    ),
    "trading_20230531": Endpoint(
        label="trading_20230531",
        dataset="trading_hourly",
        remote_date_col="거래일자",
        url="https://api.odcloud.kr/api/15065269/v1/uddi:b98e93d3-ce0d-47df-a23b-a46844552ac4",
    ),
    "trading_20231130": Endpoint(
        label="trading_20231130",
        dataset="trading_hourly",
        remote_date_col="거래일자",
        url="https://api.odcloud.kr/api/15065269/v1/uddi:4dec37b2-15e1-480b-94e3-87bdc2ecff1b",
    ),
    "trading_20231231": Endpoint(
        label="trading_20231231",
        dataset="trading_hourly",
        remote_date_col="거래일자",
        url="https://api.odcloud.kr/api/15065269/v1/uddi:0da6dc76-cff3-4759-b86f-b0ff631e5b32",
    ),
    "trading_20251231": Endpoint(
        label="trading_20251231",
        dataset="trading_hourly",
        remote_date_col="거래일",
        url="https://api.odcloud.kr/api/15065269/v1/uddi:76850689-e74c-402e-bfec-9142976b96c8",
    ),
}


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


def service_key() -> str:
    key = os.getenv("ODCLOUD_SERVICE_KEY") or os.getenv("DATA_GO_KR_SERVICE_KEY") or os.getenv("ASOS_SERVICE_KEY")
    if not key:
        raise RuntimeError("Missing service key: set ODCLOUD_SERVICE_KEY, DATA_GO_KR_SERVICE_KEY, or ASOS_SERVICE_KEY")
    return key


def endpoint_url(endpoint: Endpoint, page: int, per_page: int, key: str, start: str | None, end: str | None) -> str:
    params = {"page": page, "perPage": per_page, "serviceKey": key}
    if start:
        params[f"cond[{endpoint.remote_date_col}::GTE]"] = start
    if end:
        params[f"cond[{endpoint.remote_date_col}::LTE]"] = end
    return endpoint.url + "?" + urlencode(params)


def request_json(url: str, retries: int) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Request failed after {retries + 1} attempts: {last_error}")


def fetch_rows(
    endpoint: Endpoint,
    per_page: int,
    retries: int,
    max_pages: int | None,
    start: str | None,
    end: str | None,
) -> pd.DataFrame:
    key = service_key()
    first = request_json(endpoint_url(endpoint, 1, per_page, key, start, end), retries)
    total = int(first.get("matchCount") or first.get("totalCount") or len(first.get("data", [])))
    page_count = (total + per_page - 1) // per_page
    if max_pages is not None:
        page_count = min(page_count, max_pages)

    rows: list[dict[str, Any]] = []
    rows.extend(first.get("data", []))
    print(f"{endpoint.label}: total={total}, per_page={per_page}, pages={page_count}", flush=True)
    for page in range(2, page_count + 1):
        payload = request_json(endpoint_url(endpoint, page, per_page, key, start, end), retries)
        rows.extend(payload.get("data", []))
        if page == page_count or page % 10 == 0:
            print(f"{endpoint.label}: fetched page {page}/{page_count}, rows={len(rows)}", flush=True)
    return pd.DataFrame(rows)


def find_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    raise ValueError(f"Missing column. Tried: {', '.join(candidates)}")


def normalize_region(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .replace(
            {
                "제주": "제주도",
                "광주": "광주시",
                "대구": "대구시",
                "대전": "대전시",
                "부산": "부산시",
                "서울": "서울시",
                "세종": "세종시",
                "울산": "울산시",
                "인천": "인천시",
            }
        )
    )


def parse_date_filter(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    return pd.Timestamp(value)


def apply_date_filter(frame: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    start_ts = parse_date_filter(start)
    end_ts = parse_date_filter(end)
    if start_ts is not None:
        frame = frame[frame["trade_date_ts"] >= start_ts]
    if end_ts is not None:
        frame = frame[frame["trade_date_ts"] <= end_ts]
    return frame


def repair_corrupt_5min_values(frame: pd.DataFrame, endpoint_label: str, out_dir: Path) -> pd.DataFrame:
    work = frame.copy()
    anomalies: list[dict[str, Any]] = []
    bad_mask = work[MINUTE_COLUMNS] > CORRUPT_5MIN_WH_THRESHOLD
    bad_cells = bad_mask.stack()
    bad_cells = bad_cells[bad_cells]
    for idx, col in bad_cells.index:
        row = work.loc[idx]
        values = row[MINUTE_COLUMNS].astype(float).to_numpy(copy=True)
        pos = MINUTE_COLUMNS.index(col)
        before = values[pos - 1] if pos > 0 and values[pos - 1] <= CORRUPT_5MIN_WH_THRESHOLD else None
        after = values[pos + 1] if pos + 1 < len(values) and values[pos + 1] <= CORRUPT_5MIN_WH_THRESHOLD else None
        if before is not None and after is not None:
            replacement = float((before + after) / 2.0)
            method = "linear_neighbor"
        else:
            good = [float(v) for j, v in enumerate(values) if j != pos and v <= CORRUPT_5MIN_WH_THRESHOLD]
            replacement = float(pd.Series(good).median()) if good else 0.0
            method = "row_median"
        anomalies.append(
            {
                "endpoint": endpoint_label,
                "region": row["region"],
                "date": row["trade_date"],
                "hour0": int(row["hour0"]),
                "minute": col,
                "old_wh": float(values[pos]),
                "new_wh": replacement,
                "method": method,
            }
        )
        work.at[idx, col] = replacement

    if anomalies:
        anomaly_path = out_dir / f"{endpoint_label}_anomalies.csv"
        pd.DataFrame(anomalies).to_csv(anomaly_path, index=False, encoding="utf-8-sig")
        print(f"{endpoint_label}: repaired anomalies={len(anomalies)} -> {anomaly_path}", flush=True)
    return work


def normalize_metered_5min(frame: pd.DataFrame, endpoint_label: str, out_dir: Path, start: str | None, end: str | None) -> pd.DataFrame:
    date_col = find_column(frame, ("거래일", "거래일자"))
    hour_col = find_column(frame, ("시간", "거래시간"))
    region_col = find_column(frame, ("지역", "지역(광역시도)", "지역명"))
    fuel_col = find_column(frame, ("연료원", "발전원"))

    work = frame[[date_col, hour_col, region_col, fuel_col, *MINUTE_COLUMNS]].copy()
    work.columns = ["trade_date", "hour0", "region", "fuel_type", *MINUTE_COLUMNS]
    work["fuel_type"] = work["fuel_type"].astype(str).str.strip()
    work = work[work["fuel_type"] == "태양광"].copy()
    work["region"] = normalize_region(work["region"])
    work["trade_date_ts"] = pd.to_datetime(work["trade_date"], errors="raise")
    work = apply_date_filter(work, start, end)
    work["hour0"] = pd.to_numeric(work["hour0"], errors="raise").astype(int)
    for col in MINUTE_COLUMNS:
        work[col] = pd.to_numeric(work[col].astype(str).str.replace(",", "", regex=False), errors="raise")
    work = repair_corrupt_5min_values(work, endpoint_label, out_dir)
    work["전력거래량(MWh)"] = work[MINUTE_COLUMNS].sum(axis=1) / 1_000_000.0
    work["거래일"] = work["trade_date_ts"].dt.strftime("%Y-%m-%d")
    work["거래시간"] = work["hour0"] + 1
    work["지역"] = work["region"]
    work["연료원"] = "태양광"
    return work[["거래일", "거래시간", "지역", "연료원", "전력거래량(MWh)"]].sort_values(
        ["지역", "거래일", "거래시간"]
    )


def normalize_trading_hourly(frame: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    date_col = find_column(frame, ("거래일", "거래일자"))
    hour_col = find_column(frame, ("거래시간", "시간"))
    region_col = find_column(frame, ("지역", "지역명", "지역세부구분"))

    generation_candidates = (
        "전력거래량(MWh)",
        "태양광 발전량(MWh)",
        "태양광발전량(Mwh)",
        "태양광발전량(MWh)",
        "발전량(MWh)",
        "발전량",
        "전력거래량",
    )
    generation_col = find_column(frame, generation_candidates)

    columns = [date_col, hour_col, region_col, generation_col]
    fuel_col = None
    if "연료원" in frame.columns:
        fuel_col = "연료원"
        columns.append(fuel_col)

    work = frame[columns].copy()
    rename = {
        date_col: "trade_date",
        hour_col: "trade_hour",
        region_col: "region",
        generation_col: "generation_mwh",
    }
    if fuel_col:
        rename[fuel_col] = "fuel_type"
    work = work.rename(columns=rename)
    if "fuel_type" in work.columns:
        work["fuel_type"] = work["fuel_type"].astype(str).str.strip()
        work = work[work["fuel_type"] == "태양광"].copy()
    work["region"] = normalize_region(work["region"])
    work["trade_date_ts"] = pd.to_datetime(work["trade_date"], errors="raise")
    work = apply_date_filter(work, start, end)
    work["trade_hour"] = pd.to_numeric(work["trade_hour"], errors="raise").astype(int)
    if work["trade_hour"].min() == 0:
        work["trade_hour"] = work["trade_hour"] + 1
    work = work[work["trade_hour"].between(1, 24)].copy()
    work["generation_mwh"] = (
        work["generation_mwh"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0.0)
        .clip(lower=0.0)
    )
    work["거래일"] = work["trade_date_ts"].dt.strftime("%Y-%m-%d")
    work["거래시간"] = work["trade_hour"]
    work["지역"] = work["region"]
    work["연료원"] = "태양광"
    work["전력거래량(MWh)"] = work["generation_mwh"]
    return work[["거래일", "거래시간", "지역", "연료원", "전력거래량(MWh)"]].sort_values(
        ["지역", "거래일", "거래시간"]
    )


def write_summary(frame: pd.DataFrame, output_path: Path) -> None:
    if frame.empty:
        print(f"{output_path.name}: no rows after filtering")
        return
    summary = (
        frame.assign(ts=pd.to_datetime(frame["거래일"]) + pd.to_timedelta(frame["거래시간"].astype(int) - 1, unit="h"))
        .groupby("지역", as_index=False)
        .agg(
            rows=("전력거래량(MWh)", "size"),
            start=("ts", "min"),
            end=("ts", "max"),
            total_mwh=("전력거래량(MWh)", "sum"),
        )
        .sort_values("지역")
    )
    summary_path = output_path.with_suffix(".summary.csv")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False))
    print(f"summary -> {summary_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--endpoint",
        action="append",
        choices=sorted(ENDPOINTS),
        required=True,
        help="Endpoint label to fetch. Repeatable.",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--start", help="Inclusive trade-date filter, YYYY-MM-DD")
    parser.add_argument("--end", help="Inclusive trade-date filter, YYYY-MM-DD")
    parser.add_argument("--per-page", type=int, default=10000)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-pages", type=int, default=None, help="Debug limit")
    parser.add_argument("--raw", action="store_true", help="Also save raw endpoint CSV")
    parser.add_argument("--input-raw", type=Path, help="Reuse an already downloaded raw CSV for a single endpoint")
    return parser.parse_args()


def main() -> None:
    load_env_files()
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.input_raw and len(args.endpoint) != 1:
        raise SystemExit("--input-raw can only be used with exactly one --endpoint")

    for endpoint_label in args.endpoint:
        endpoint = ENDPOINTS[endpoint_label]
        if args.input_raw:
            raw = pd.read_csv(args.input_raw)
            print(f"raw <- {args.input_raw} rows={len(raw)}", flush=True)
        else:
            raw = fetch_rows(endpoint, args.per_page, args.retries, args.max_pages, args.start, args.end)
        if args.raw:
            raw_path = args.out_dir / f"{endpoint.label}_raw.csv"
            raw.to_csv(raw_path, index=False, encoding="utf-8-sig")
            print(f"raw -> {raw_path}")

        if endpoint.dataset == "metered_5min":
            normalized = normalize_metered_5min(raw, endpoint.label, args.out_dir, args.start, args.end)
        elif endpoint.dataset == "trading_hourly":
            normalized = normalize_trading_hourly(raw, args.start, args.end)
        else:
            raise ValueError(f"Unsupported endpoint dataset: {endpoint.dataset}")

        output_path = args.out_dir / f"{endpoint.label}_normalized.csv"
        normalized.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"normalized -> {output_path} rows={len(normalized)}")
        write_summary(normalized, output_path)


if __name__ == "__main__":
    main()
