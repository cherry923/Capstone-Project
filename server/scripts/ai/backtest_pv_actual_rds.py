#!/usr/bin/env python3
"""
Backtest PV forecasting models against RDS pv_actual_hourly_data labels.

The default split trains on 2025-01..09 and validates on 2025-10..12.
Weather features are optional. When enabled, they use target-hour observed ASOS
weather, so the result is an offline upper bound, not a production forecast.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

import numpy as np
import pandas as pd
import psycopg2
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = PROJECT_ROOT / "ai_module" / "artifacts"
ENV_PATHS = (
    PROJECT_ROOT / ".env",
    PROJECT_ROOT / "server" / ".env",
)
DEFAULT_SOURCE = "KPX_REGIONAL_HOURLY_SOLAR_WIND"
DEFAULT_FUEL = "태양광"
DEFAULT_CAPACITY_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pv"
    / "capacity_20260519"
    / "kpx_regional_solar_capacity_monthly_202210_202505.csv"
)
BASE_FEATURES = [
    "hour_sin",
    "hour_cos",
    "doy_sin",
    "doy_cos",
    "dow_sin",
    "dow_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
    "lag24",
    "lag48",
    "lag72",
    "lag168",
    "rolling24_mean",
    "rolling168_mean",
]
WEATHER_FEATURES = [
    "temperature",
    "rainfall",
    "humidity",
    "snowfall",
    "cloud_cover",
    "sunshine_duration",
    "solar_radiation",
    "wind_speed",
]
WEATHER_LAG_FEATURES = [
    "solar_radiation_lag24",
    "solar_radiation_lag168",
    "sunshine_duration_lag24",
    "sunshine_duration_lag168",
]
CAPACITY_FEATURES = [
    "solar_capacity_mw",
    "solar_capacity_lag24",
    "solar_capacity_lag168",
    "capacity_growth_30d",
    "capacity_growth_180d",
]
ESTIMATED_CAPACITY_FEATURES = [
    "estimated_capacity_index_30d",
    "estimated_capacity_index_90d",
    "estimated_capacity_growth_30d",
    "estimated_capacity_growth_90d",
]


@dataclass(frozen=True)
class DbConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


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
    return {
        "host": parsed.hostname or "",
        "port": str(parsed.port or 5432),
        "dbname": parsed.path.lstrip("/"),
        **dict(parse_qsl(parsed.query)),
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


def load_pv_actual(region: str, source: str, fuel: str, start: str, end: str) -> pd.DataFrame:
    query = """
        SELECT observed_at AS ts, generation_mwh AS y
        FROM pv_actual_hourly_data
        WHERE source = %s
          AND region = %s
          AND fuel_type = %s
          AND observed_at >= %s
          AND observed_at < %s
        ORDER BY observed_at
    """
    with connect() as conn:
        frame = pd.read_sql_query(query, conn, params=(source, region, fuel, start, end))
    if frame.empty:
        raise RuntimeError(f"No PV rows found for region={region}, source={source}, fuel={fuel}")
    frame["ts"] = pd.to_datetime(frame["ts"])
    frame["y"] = pd.to_numeric(frame["y"], errors="coerce").fillna(0.0).clip(lower=0.0)
    return frame.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def load_weather(station_id: int, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    query = """
        SELECT observation_time AS ts,
               temperature,
               rainfall,
               humidity,
               snowfall,
               cloud_cover,
               sunshine_duration,
               solar_radiation,
               wind_speed
        FROM weather_raw_data
        WHERE asos_station_id = %s
          AND observation_time >= %s
          AND observation_time <= %s
        ORDER BY observation_time
    """
    with connect() as conn:
        frame = pd.read_sql_query(query, conn, params=(station_id, start.to_pydatetime(), end.to_pydatetime()))
    if frame.empty:
        raise RuntimeError(f"No weather rows found for ASOS station {station_id}")
    frame["ts"] = pd.to_datetime(frame["ts"])
    for col in WEATHER_FEATURES:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    zero_cols = ["rainfall", "snowfall", "sunshine_duration", "solar_radiation"]
    smooth_cols = ["temperature", "humidity", "cloud_cover", "wind_speed"]
    frame[zero_cols] = frame[zero_cols].fillna(0.0)
    frame[smooth_cols] = frame[smooth_cols].interpolate(limit_direction="both").ffill().bfill().fillna(0.0)
    return frame.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def load_weather_features(
    station_ids: list[int],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, list[str], str]:
    if not station_ids:
        raise ValueError("station_ids must not be empty")

    merged: pd.DataFrame | None = None
    station_feature_cols: dict[str, list[str]] = {col: [] for col in WEATHER_FEATURES}
    for station_id in station_ids:
        weather = load_weather(station_id, start, end)
        rename_map = {col: f"asos{station_id}_{col}" for col in WEATHER_FEATURES}
        station_frame = weather.rename(columns=rename_map)
        for col in WEATHER_FEATURES:
            station_feature_cols[col].append(rename_map[col])
        merged = station_frame if merged is None else merged.merge(station_frame, on="ts", how="outer")

    assert merged is not None
    merged = merged.sort_values("ts").reset_index(drop=True)
    all_station_cols = [col for cols in station_feature_cols.values() for col in cols]
    merged[all_station_cols] = merged[all_station_cols].interpolate(limit_direction="both").ffill().bfill()

    extra_cols: list[str] = []
    for col, station_cols in station_feature_cols.items():
        merged[col] = merged[station_cols].mean(axis=1)
        if len(station_ids) > 1 and col in {"solar_radiation", "sunshine_duration", "cloud_cover", "rainfall"}:
            max_col = f"{col}_station_max"
            min_col = f"{col}_station_min"
            spread_col = f"{col}_station_spread"
            merged[max_col] = merged[station_cols].max(axis=1)
            merged[min_col] = merged[station_cols].min(axis=1)
            merged[spread_col] = merged[max_col] - merged[min_col]
            extra_cols.extend([max_col, min_col, spread_col])

    keep_cols = ["ts", *WEATHER_FEATURES, *extra_cols]
    mode = "actual_asos_" + "_".join(str(station_id) for station_id in station_ids) + "_oracle"
    return merged[keep_cols], extra_cols, mode


def normalize_region(value: str) -> str:
    return {
        "서울특별시": "서울시",
        "부산광역시": "부산시",
        "대구광역시": "대구시",
        "인천광역시": "인천시",
        "광주광역시": "광주시",
        "대전광역시": "대전시",
        "울산광역시": "울산시",
        "세종특별자치시": "세종시",
        "제주특별자치도": "제주도",
        "서울": "서울시",
        "부산": "부산시",
        "대구": "대구시",
        "인천": "인천시",
        "광주": "광주시",
        "대전": "대전시",
        "울산": "울산시",
        "세종": "세종시",
        "제주": "제주도",
    }.get(value.strip(), value.strip())


def load_capacity(region: str, capacity_csv: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if not capacity_csv.exists():
        raise FileNotFoundError(f"Capacity CSV not found: {capacity_csv}")
    frame = pd.read_csv(capacity_csv)
    frame["region"] = frame["region"].astype(str).map(normalize_region)
    frame = frame[frame["region"] == normalize_region(region)].copy()
    if frame.empty:
        raise RuntimeError(f"No capacity rows found for region={region}, csv={capacity_csv}")
    frame["month_start"] = pd.to_datetime(frame["month_start"])
    frame["solar_capacity_mw"] = pd.to_numeric(frame["solar_capacity_mw"], errors="coerce")
    frame = frame.dropna(subset=["month_start", "solar_capacity_mw"]).sort_values("month_start")

    month_index = pd.date_range(
        pd.Timestamp(start).to_period("M").to_timestamp(),
        pd.Timestamp(end).to_period("M").to_timestamp(),
        freq="MS",
    )
    out = pd.DataFrame({"month_start": month_index})
    out = out.merge(frame[["month_start", "solar_capacity_mw"]], on="month_start", how="left")
    out["solar_capacity_mw"] = out["solar_capacity_mw"].ffill().bfill()
    out["capacity_backfilled"] = ~out["month_start"].isin(set(frame["month_start"]))
    out["region"] = normalize_region(region)
    return out


def add_time_and_lag_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.sort_values("ts").reset_index(drop=True).copy()
    hour = out["ts"].dt.hour
    doy = out["ts"].dt.dayofyear
    dow = out["ts"].dt.dayofweek
    month = out["ts"].dt.month
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    out["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    out["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
    out["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)
    out["month_sin"] = np.sin(2 * np.pi * month / 12.0)
    out["month_cos"] = np.cos(2 * np.pi * month / 12.0)
    out["is_weekend"] = (dow >= 5).astype(float)
    for lag in (24, 48, 72, 168):
        out[f"lag{lag}"] = out["y"].shift(lag)
    shifted = out["y"].shift(1)
    out["rolling24_mean"] = shifted.rolling(24, min_periods=24).mean()
    out["rolling168_mean"] = shifted.rolling(168, min_periods=168).mean()
    daylight_generation = out["y"].where(hour.between(8, 16)).shift(1)
    out["estimated_capacity_index_30d"] = (
        daylight_generation.rolling(24 * 30, min_periods=24 * 7).quantile(0.98).ffill().bfill()
    )
    out["estimated_capacity_index_90d"] = (
        daylight_generation.rolling(24 * 90, min_periods=24 * 14).quantile(0.98).ffill().bfill()
    )
    out["estimated_capacity_growth_30d"] = (
        out["estimated_capacity_index_30d"] / out["estimated_capacity_index_30d"].shift(24 * 30) - 1.0
    )
    out["estimated_capacity_growth_90d"] = (
        out["estimated_capacity_index_90d"] / out["estimated_capacity_index_90d"].shift(24 * 90) - 1.0
    )
    out[["estimated_capacity_growth_30d", "estimated_capacity_growth_90d"]] = out[
        ["estimated_capacity_growth_30d", "estimated_capacity_growth_90d"]
    ].fillna(0.0)
    return out


def prepare_frame(
    region: str,
    source: str,
    fuel: str,
    start: str,
    end: str,
    weather_station_ids: list[int] | None,
    capacity_csv: Path | None,
) -> tuple[pd.DataFrame, list[str], str, str]:
    frame = add_time_and_lag_features(load_pv_actual(region, source, fuel, start, end))
    feature_cols = [*BASE_FEATURES, *ESTIMATED_CAPACITY_FEATURES]
    weather_mode = "none"
    if weather_station_ids:
        weather, extra_weather_cols, weather_mode = load_weather_features(
            weather_station_ids,
            frame["ts"].min(),
            frame["ts"].max(),
        )
        frame = frame.merge(weather, on="ts", how="left")
        frame[[*WEATHER_FEATURES, *extra_weather_cols]] = frame[
            [*WEATHER_FEATURES, *extra_weather_cols]
        ].interpolate(limit_direction="both").ffill().bfill()
        feature_cols.extend([*WEATHER_FEATURES, *extra_weather_cols])
        for col in ("solar_radiation", "sunshine_duration"):
            for lag in (24, 168):
                frame[f"{col}_lag{lag}"] = frame[col].shift(lag)
        feature_cols.extend(WEATHER_LAG_FEATURES)
    capacity_mode = "none"
    if capacity_csv is not None:
        capacity = load_capacity(region, capacity_csv, frame["ts"].min(), frame["ts"].max())
        frame["month_start"] = frame["ts"].dt.to_period("M").dt.to_timestamp()
        frame = frame.merge(capacity[["month_start", "solar_capacity_mw"]], on="month_start", how="left")
        frame["solar_capacity_mw"] = frame["solar_capacity_mw"].ffill().bfill()
        frame["solar_capacity_lag24"] = frame["solar_capacity_mw"].shift(24)
        frame["solar_capacity_lag168"] = frame["solar_capacity_mw"].shift(168)
        frame["capacity_growth_30d"] = frame["solar_capacity_mw"] / frame["solar_capacity_mw"].shift(24 * 30) - 1.0
        frame["capacity_growth_180d"] = frame["solar_capacity_mw"] / frame["solar_capacity_mw"].shift(24 * 180) - 1.0
        frame[["capacity_growth_30d", "capacity_growth_180d"]] = frame[
            ["capacity_growth_30d", "capacity_growth_180d"]
        ].fillna(0.0)
        feature_cols.extend(CAPACITY_FEATURES)
        capacity_mode = f"kpx_monthly_capacity:{rel(capacity_csv)}"
    frame = frame.dropna(subset=[*feature_cols, "y"]).reset_index(drop=True)
    return frame, feature_cols, weather_mode, capacity_mode


def wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = float(np.sum(np.abs(y_true)))
    if denom <= 1e-9:
        return float("nan")
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true > 1e-6
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def fit_ratio_model(
    estimator,
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_cols: list[str],
    baseline_col: str,
) -> np.ndarray:
    x_train = train[feature_cols].to_numpy(dtype=float)
    x_test = test[feature_cols].to_numpy(dtype=float)
    y_train = train["y"].to_numpy(dtype=float)
    train_baseline = train[baseline_col].to_numpy(dtype=float)
    test_baseline = test[baseline_col].to_numpy(dtype=float)

    usable = train_baseline > 1e-6
    if not usable.any():
        return np.zeros(len(test), dtype=float)

    ratio_target = np.divide(
        y_train[usable],
        train_baseline[usable],
        out=np.zeros(int(usable.sum()), dtype=float),
        where=train_baseline[usable] > 1e-6,
    )
    ratio_target = np.clip(ratio_target, 0.0, 4.0)
    ratio_pred = np.clip(estimator.fit(x_train[usable], ratio_target).predict(x_test), 0.0, 4.0)
    return np.where(test_baseline > 1e-6, ratio_pred * test_baseline, 0.0)


def weather_scaled_lag(test: pd.DataFrame, lag: int) -> np.ndarray:
    lag_col = f"lag{lag}"
    radiation_lag_col = f"solar_radiation_lag{lag}"
    sunshine_lag_col = f"sunshine_duration_lag{lag}"
    required = {lag_col, "solar_radiation", radiation_lag_col, "sunshine_duration", sunshine_lag_col}
    if not required.issubset(test.columns):
        return np.full(len(test), np.nan, dtype=float)

    base = test[lag_col].to_numpy(dtype=float)
    radiation_now = test["solar_radiation"].to_numpy(dtype=float)
    radiation_prev = test[radiation_lag_col].to_numpy(dtype=float)
    sunshine_now = test["sunshine_duration"].to_numpy(dtype=float)
    sunshine_prev = test[sunshine_lag_col].to_numpy(dtype=float)

    radiation_ratio = np.clip((radiation_now + 0.05) / (radiation_prev + 0.05), 0.0, 3.0)
    sunshine_ratio = np.clip((sunshine_now + 0.05) / (sunshine_prev + 0.05), 0.0, 3.0)
    weather_ratio = 0.75 * radiation_ratio + 0.25 * sunshine_ratio
    pred = base * weather_ratio
    pred = np.where((radiation_now <= 0.02) & (sunshine_now <= 0.02), 0.0, pred)
    return np.clip(pred, 0.0, None)


def fit_scale_factor_model(
    estimator,
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_cols: list[str],
    scale_col: str,
) -> np.ndarray:
    if scale_col not in train.columns or scale_col not in test.columns:
        return np.full(len(test), np.nan, dtype=float)
    train_scale = train[scale_col].to_numpy(dtype=float)
    test_scale = test[scale_col].to_numpy(dtype=float)
    usable = train_scale > 1e-6
    if not usable.any():
        return np.zeros(len(test), dtype=float)
    x_train = train[feature_cols].to_numpy(dtype=float)
    x_test = test[feature_cols].to_numpy(dtype=float)
    y_train = train["y"].to_numpy(dtype=float)
    target = np.clip(y_train[usable] / train_scale[usable], 0.0, 2.5)
    factor_pred = np.clip(estimator.fit(x_train[usable], target).predict(x_test), 0.0, 2.5)
    return factor_pred * test_scale


def metric_row(model: str, test: pd.DataFrame, y_pred: np.ndarray, feature_mode: str) -> dict[str, object]:
    y_true = test["y"].to_numpy(dtype=float)
    daylight = test["ts"].dt.hour.between(6, 18).to_numpy()
    daily = (
        pd.DataFrame({"date": test["ts"].dt.date, "y": y_true, "pred": y_pred})
        .groupby("date", as_index=False)
        .sum(numeric_only=True)
    )
    return {
        "feature_mode": feature_mode,
        "model": model,
        "rows": int(len(test)),
        "days": int(test["ts"].dt.date.nunique()),
        "mae_mwh": float(mean_absolute_error(y_true, y_pred)),
        "rmse_mwh": rmse(y_true, y_pred),
        "wape_percent": wape(y_true, y_pred),
        "mape_percent": mape(y_true, y_pred),
        "daylight_mae_mwh": float(mean_absolute_error(y_true[daylight], y_pred[daylight])),
        "daylight_wape_percent": wape(y_true[daylight], y_pred[daylight]),
        "daily_sum_wape_percent": wape(daily["y"].to_numpy(dtype=float), daily["pred"].to_numpy(dtype=float)),
    }


def fit_predict_models(train: pd.DataFrame, test: pd.DataFrame, feature_cols: list[str]) -> dict[str, np.ndarray]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = train["y"].to_numpy(dtype=float)
    x_test = test[feature_cols].to_numpy(dtype=float)
    predictions = {
        "naive_lag24": test["lag24"].to_numpy(dtype=float),
        "naive_lag168": test["lag168"].to_numpy(dtype=float),
        "linear_regression": np.clip(
            make_pipeline(StandardScaler(), LinearRegression()).fit(x_train, y_train).predict(x_test),
            0.0,
            None,
        ),
        "ridge": np.clip(
            make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(x_train, y_train).predict(x_test),
            0.0,
            None,
        ),
        "random_forest": np.clip(
            RandomForestRegressor(
                n_estimators=300,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            )
            .fit(x_train, y_train)
            .predict(x_test),
            0.0,
            None,
        ),
        "extra_trees": np.clip(
            ExtraTreesRegressor(
                n_estimators=400,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            )
            .fit(x_train, y_train)
            .predict(x_test),
            0.0,
            None,
        ),
    }
    predictions["ratio_random_forest_rolling168"] = fit_ratio_model(
        RandomForestRegressor(
            n_estimators=300,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
        train,
        test,
        feature_cols,
        "rolling168_mean",
    )
    predictions["ratio_extra_trees_rolling168"] = fit_ratio_model(
        ExtraTreesRegressor(
            n_estimators=400,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
        train,
        test,
        feature_cols,
        "rolling168_mean",
    )
    if {"solar_radiation", "solar_radiation_lag24", "solar_radiation_lag168"}.issubset(test.columns):
        weather_lag24 = weather_scaled_lag(test, 24)
        weather_lag168 = weather_scaled_lag(test, 168)
        predictions["weather_scaled_lag24"] = weather_lag24
        predictions["weather_scaled_lag168"] = weather_lag168
        predictions["weather_scaled_lag_blend"] = np.nanmean(
            np.vstack([weather_lag24, weather_lag168]),
            axis=0,
        )
    if "solar_capacity_mw" in train.columns:
        predictions["capacity_factor_random_forest"] = fit_scale_factor_model(
            RandomForestRegressor(
                n_estimators=300,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            ),
            train,
            test,
            feature_cols,
            "solar_capacity_mw",
        )
        predictions["capacity_factor_extra_trees"] = fit_scale_factor_model(
            ExtraTreesRegressor(
                n_estimators=400,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            ),
            train,
            test,
            feature_cols,
            "solar_capacity_mw",
        )
    if "estimated_capacity_index_90d" in train.columns:
        predictions["estimated_capacity_factor_extra_trees_90d"] = fit_scale_factor_model(
            ExtraTreesRegressor(
                n_estimators=400,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            ),
            train,
            test,
            feature_cols,
            "estimated_capacity_index_90d",
        )
        predictions["estimated_capacity_factor_random_forest_90d"] = fit_scale_factor_model(
            RandomForestRegressor(
                n_estimators=300,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            ),
            train,
            test,
            feature_cols,
            "estimated_capacity_index_90d",
        )
        predictions["estimated_capacity_factor_extra_trees_30d"] = fit_scale_factor_model(
            ExtraTreesRegressor(
                n_estimators=400,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            ),
            train,
            test,
            feature_cols,
            "estimated_capacity_index_30d",
        )
        predictions["estimated_capacity_factor_hgb_90d"] = fit_scale_factor_model(
            HistGradientBoostingRegressor(
                max_iter=500,
                learning_rate=0.05,
                max_leaf_nodes=31,
                l2_regularization=0.01,
                loss="squared_error",
                random_state=42,
            ),
            train,
            test,
            feature_cols,
            "estimated_capacity_index_90d",
        )
    return predictions


def run_backtest(
    region: str,
    source: str,
    fuel: str,
    data_start: str,
    data_end: str,
    train_end: str,
    test_start: str,
    test_end: str,
    weather_station_ids: list[int] | None,
    capacity_csv: Path | None,
    output_stem: str,
) -> tuple[Path, Path, dict[str, object]]:
    frame, feature_cols, weather_mode, capacity_mode = prepare_frame(
        region,
        source,
        fuel,
        data_start,
        data_end,
        weather_station_ids,
        capacity_csv,
    )
    train = frame[(frame["ts"] >= pd.Timestamp(data_start)) & (frame["ts"] < pd.Timestamp(train_end))].copy()
    test = frame[(frame["ts"] >= pd.Timestamp(test_start)) & (frame["ts"] < pd.Timestamp(test_end))].copy()
    if train.empty or test.empty:
        raise RuntimeError(f"Empty train/test split: train={len(train)}, test={len(test)}")

    predictions = fit_predict_models(train, test, feature_cols)
    summary = pd.DataFrame(
        [metric_row(model, test, pred, weather_mode) for model, pred in predictions.items()]
    ).sort_values(["wape_percent", "mae_mwh"])

    pred_frame = test[["ts", "y"]].rename(columns={"y": "actual_mwh"}).copy()
    for model, pred in predictions.items():
        pred_frame[f"{model}_mwh"] = pred
    pred_frame["region"] = region
    pred_frame["feature_mode"] = weather_mode

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = ARTIFACT_DIR / f"{output_stem}.json"
    pred_path = ARTIFACT_DIR / f"{output_stem}_predictions.csv"
    csv_summary_path = ARTIFACT_DIR / f"{output_stem}.csv"
    summary.to_csv(csv_summary_path, index=False, encoding="utf-8")
    pred_frame.to_csv(pred_path, index=False, encoding="utf-8")

    payload: dict[str, object] = {
        "dataset": {
            "source": source,
            "region": region,
            "fuel_type": fuel,
            "data_range": [str(frame["ts"].min()), str(frame["ts"].max())],
            "train_range": [data_start, train_end],
            "test_range": [test_start, test_end],
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "weather_mode": weather_mode,
            "capacity_mode": capacity_mode,
            "feature_columns": feature_cols,
        },
        "summary": summary.to_dict(orient="records"),
        "artifacts": {
            "summary_csv": rel(csv_summary_path),
            "predictions_csv": rel(pred_path),
        },
        "notes": [
            "All target labels come from RDS pv_actual_hourly_data.",
            "Lag features are shifted from past actual PV only.",
            "Estimated capacity index features use only shifted past actual PV generation.",
            "actual_asos_* uses target-hour observed weather and is therefore an offline upper-bound validation.",
            "kpx_monthly_capacity joins official monthly regional PV capacity and forward-fills months beyond the latest file month.",
            "This script does not run Han TFT best_model.pt because the current default Python environment has no torch installed.",
        ],
    }
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary_path, pred_path, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="제주도")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--fuel", default=DEFAULT_FUEL)
    parser.add_argument("--data-start", default="2025-01-01")
    parser.add_argument("--data-end", default="2026-01-01")
    parser.add_argument("--train-end", default="2025-10-01")
    parser.add_argument("--test-start", default="2025-10-01")
    parser.add_argument("--test-end", default="2026-01-01")
    parser.add_argument("--weather-station-id", type=int, default=None)
    parser.add_argument("--weather-station-ids", nargs="+", type=int, default=None)
    parser.add_argument(
        "--capacity-csv",
        type=Path,
        default=None,
        help=f"Optional monthly regional solar capacity CSV, e.g. {rel(DEFAULT_CAPACITY_CSV)}",
    )
    parser.add_argument("--output-stem", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env_files()
    weather_station_ids = args.weather_station_ids
    if weather_station_ids is None and args.weather_station_id is not None:
        weather_station_ids = [args.weather_station_id]
    output_stem = args.output_stem or (
        f"pv_actual_rds_{args.region}_{'asos' + '_'.join(map(str, weather_station_ids)) if weather_station_ids else 'lag'}"
    )
    output_stem = output_stem.replace("/", "_").replace(" ", "_")
    summary_path, pred_path, payload = run_backtest(
        region=args.region,
        source=args.source,
        fuel=args.fuel,
        data_start=args.data_start,
        data_end=args.data_end,
        train_end=args.train_end,
        test_start=args.test_start,
        test_end=args.test_end,
        weather_station_ids=weather_station_ids,
        capacity_csv=args.capacity_csv,
        output_stem=output_stem,
    )
    print(f"saved: {rel(summary_path)}")
    print(f"saved: {rel(pred_path)}")
    print("[summary]")
    for row in payload["summary"]:  # type: ignore[index]
        print(
            f"- {row['feature_mode']} / {row['model']}: "
            f"mae={row['mae_mwh']:.3f} MWh, rmse={row['rmse_mwh']:.3f} MWh, "
            f"wape={row['wape_percent']:.2f}%, daylight_wape={row['daylight_wape_percent']:.2f}%, "
            f"daily_sum_wape={row['daily_sum_wape_percent']:.2f}%"
        )


if __name__ == "__main__":
    main()
