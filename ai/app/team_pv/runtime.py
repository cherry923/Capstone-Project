from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn


TIMESTAMP_ALIASES = ["일시", "시각", "timestamp", "datetime", "date"]
MODEL_FEATURES = ["기온", "강수량", "습도", "적설량", "구름량", "일조시간", "일사량"]
WEATHER_COLUMN_ALIASES = {
    "기온": ["기온", "기온(°C)", "temperature", "temp"],
    "강수량": ["강수량", "강수량(mm)", "rainfall", "precipitation", "rain"],
    "습도": ["습도", "습도(%)", "humidity"],
    "적설량": ["적설량", "적설(cm)", "snow", "snowfall"],
    "구름량": ["구름량", "전운량(10분위)", "cloud", "cloud_cover"],
    "일조시간": ["일조시간", "일조(hr)", "sunshine_duration", "duration"],
    "일사량": ["일사량", "일사(MJ/m2)", "solar_radiation", "radiation", "irradiance"],
}


@dataclass
class HanPVConfig:
    station_name: str = "인천시"
    weather_station_name: str = "인천"
    encoder_length: int = 168
    decoder_length: int = 24
    prediction_length: int = 24
    hidden_size: int = 64
    lstm_layers: int = 2
    attention_heads: int = 4
    dropout: float = 0.1
    batch_size: int = 64
    learning_rate: float = 1e-3
    max_epochs: int = 30
    seed: int = 42
    train_start: str = "2025-01-01"
    train_end: str = "2025-07-01"
    test_start: str = "2025-07-01"
    test_end: str = "2025-08-01"


def read_csv_auto(path: str | Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"CSV encoding failed: {path}")


def find_first_column(columns: list[str], aliases: list[str], label: str) -> str:
    for alias in aliases:
        if alias in columns:
            return alias
    raise ValueError(f"{label} column not found. candidates={aliases}")


def masked_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    valid = y_true > 1e-6
    if not valid.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[valid] - y_pred[valid]) / y_true[valid])) * 100.0)


class StandardScaler1D:
    def __init__(self, mean: np.ndarray | None = None, std: np.ndarray | None = None) -> None:
        self.mean_ = mean
        self.std_ = std

    def fit(self, values: np.ndarray) -> "StandardScaler1D":
        self.mean_ = values.mean(axis=0, keepdims=True)
        self.std_ = values.std(axis=0, keepdims=True)
        self.std_[self.std_ < 1e-6] = 1.0
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.std_ is None:
            raise ValueError("scaler is not fitted")
        return (values - self.mean_) / self.std_

    def inverse_transform(self, values: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.std_ is None:
            raise ValueError("scaler is not fitted")
        return values * self.std_ + self.mean_

    def to_dict(self) -> dict[str, Any]:
        if self.mean_ is None or self.std_ is None:
            raise ValueError("scaler is not fitted")
        return {"mean": self.mean_.tolist(), "std": self.std_.tolist()}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StandardScaler1D":
        return cls(
            mean=np.array(payload["mean"], dtype=np.float32),
            std=np.array(payload["std"], dtype=np.float32),
        )


class DataRepository:
    def __init__(self, config: HanPVConfig) -> None:
        self.config = config

    def load_pv_data(self, pv_path: str | Path) -> pd.DataFrame:
        frame = read_csv_auto(pv_path)
        if "연료원" in frame.columns:
            frame = frame[frame["연료원"] == "태양광"].copy()
        if "지역" in frame.columns:
            frame = frame[frame["지역"] == self.config.station_name].copy()
        if frame.empty:
            raise ValueError(f"PV rows not found for station={self.config.station_name}")

        frame["거래시간"] = pd.to_numeric(frame["거래시간"], errors="coerce")
        frame["시각"] = pd.to_datetime(frame["거래일"]) + pd.to_timedelta(
            frame["거래시간"] - 1, unit="h"
        )
        frame = frame.rename(columns={"전력거래량(MWh)": "실제발전량"})
        frame["실제발전량"] = pd.to_numeric(frame["실제발전량"], errors="coerce").fillna(0.0)
        frame["실제발전량"] = frame["실제발전량"].clip(lower=0.0)
        frame["설비용량"] = 1.0
        return frame[["시각", "실제발전량", "설비용량"]].sort_values("시각").reset_index(drop=True)

    def load_weather_data(self, weather_path: str | Path) -> pd.DataFrame:
        path = Path(weather_path)
        if path.is_dir():
            files = sorted(path.glob("OBS_ASOS_TIM_*.csv")) + sorted(path.glob("OBS_ASOS_TIM_*.CSV"))
            if not files:
                raise FileNotFoundError(f"OBS_ASOS CSV not found: {path}")
            raw = pd.concat([read_csv_auto(item) for item in files], ignore_index=True)
        else:
            raw = read_csv_auto(path)

        if "지점명" in raw.columns:
            filtered = raw[raw["지점명"].astype(str) == self.config.weather_station_name].copy()
            if not filtered.empty:
                raw = filtered
        return self._standardize_weather_columns(raw)

    def _standardize_weather_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = df.copy()
        timestamp_col = find_first_column(list(renamed.columns), TIMESTAMP_ALIASES, "timestamp")
        renamed = renamed.rename(columns={timestamp_col: "시각"})
        for standard_name, aliases in WEATHER_COLUMN_ALIASES.items():
            match = next((alias for alias in aliases if alias in renamed.columns), None)
            if match is None:
                raise ValueError(f"{standard_name} column not found")
            renamed = renamed.rename(columns={match: standard_name})
        return renamed[["시각", *MODEL_FEATURES]].copy()


class PVDataProcessor:
    def merge_and_clean(self, pv_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
        pv = pv_df.copy()
        weather = weather_df.copy()
        pv["시각"] = pd.to_datetime(pv["시각"])
        weather["시각"] = pd.to_datetime(weather["시각"])

        for col in ["실제발전량", "설비용량"]:
            pv[col] = pd.to_numeric(pv[col], errors="coerce")

        merged = pv.merge(weather, on="시각", how="left", suffixes=("_pv", ""))
        for col in MODEL_FEATURES:
            pv_col = f"{col}_pv"
            if pv_col in merged.columns:
                merged[col] = pd.to_numeric(merged[col], errors="coerce").combine_first(
                    pd.to_numeric(merged[pv_col], errors="coerce")
                )
                merged = merged.drop(columns=[pv_col])
            else:
                merged[col] = pd.to_numeric(merged[col], errors="coerce")

        merged["실제발전량"] = pd.to_numeric(merged["실제발전량"], errors="coerce").fillna(0.0)
        merged["실제발전량"] = merged["실제발전량"].clip(lower=0.0)
        merged["설비용량"] = pd.to_numeric(merged["설비용량"], errors="coerce").ffill().bfill()
        for col in ["강수량", "적설량", "구름량", "일조시간", "일사량"]:
            merged[col] = merged[col].fillna(0.0)
        for col in ["기온", "습도"]:
            merged[col] = merged[col].interpolate(limit_direction="both").ffill().bfill()
        return (
            merged.dropna(subset=["시각", "실제발전량", "설비용량"])
            .sort_values("시각")
            .drop_duplicates(subset=["시각"])
            .reset_index(drop=True)
        )


class FeatureEngineer:
    @property
    def encoder_features(self) -> list[str]:
        return [
            *MODEL_FEATURES,
            "irradiance_sq",
            "cloud_inv",
            "hour_sin",
            "hour_cos",
            "day_sin",
            "day_cos",
            "is_weekend",
            "log_capacity",
        ]

    def build_training_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        frame = self._add_time_features(df)
        max_pv = frame["실제발전량"].max()
        if pd.isna(max_pv) or max_pv <= 0:
            raise ValueError("PV maximum is <= 0")
        frame["pv_max"] = max_pv
        frame["pv_norm"] = frame["실제발전량"] / (max_pv + 1e-6)
        frame["pv_norm"] = frame["pv_norm"].fillna(0.0).clip(lower=0.0)
        frame["log_capacity"] = 0.0
        return frame

    def build_inference_features(self, weather_rows: list[dict[str, Any]], timestamps: list[pd.Timestamp]) -> pd.DataFrame:
        rows = []
        for row, timestamp in zip(weather_rows, timestamps, strict=True):
            normalized = {"시각": timestamp}
            for feature, aliases in WEATHER_COLUMN_ALIASES.items():
                normalized[feature] = _first_numeric(row, aliases)
            rows.append(normalized)
        frame = pd.DataFrame(rows)
        for col in ["강수량", "적설량", "구름량", "일조시간", "일사량"]:
            frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0.0)
        for col in ["기온", "습도"]:
            frame[col] = pd.to_numeric(frame[col], errors="coerce").interpolate(limit_direction="both").ffill().bfill()
        frame["실제발전량"] = 0.0
        frame["설비용량"] = 1.0
        frame = self._add_time_features(frame)
        frame["log_capacity"] = 0.0
        return frame

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        frame = df.copy().sort_values("시각").reset_index(drop=True)
        frame["시각"] = pd.to_datetime(frame["시각"])
        frame["hour"] = frame["시각"].dt.hour
        frame["dayofyear"] = frame["시각"].dt.dayofyear
        frame["weekday"] = frame["시각"].dt.weekday
        frame["is_weekend"] = (frame["weekday"] >= 5).astype(float)
        frame["irradiance_sq"] = pd.to_numeric(frame["일사량"], errors="coerce").fillna(0.0) ** 2
        frame["cloud_inv"] = 1 / (pd.to_numeric(frame["구름량"], errors="coerce").fillna(0.0) + 1)
        frame["hour_sin"] = np.sin(2 * np.pi * frame["hour"] / 24.0)
        frame["hour_cos"] = np.cos(2 * np.pi * frame["hour"] / 24.0)
        frame["day_sin"] = np.sin(2 * np.pi * frame["dayofyear"] / 365.25)
        frame["day_cos"] = np.cos(2 * np.pi * frame["dayofyear"] / 365.25)
        return frame


class GatedResidualNetwork(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, output_size: int, dropout: float) -> None:
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.elu = nn.ELU()
        self.fc2 = nn.Linear(hidden_size, output_size)
        self.dropout = nn.Dropout(dropout)
        self.gate = nn.Linear(output_size, output_size)
        self.skip = nn.Linear(input_size, output_size) if input_size != output_size else nn.Identity()
        self.norm = nn.LayerNorm(output_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.skip(x)
        out = self.fc1(x)
        out = self.elu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        gated = torch.sigmoid(self.gate(out)) * out
        return self.norm(residual + gated)


class VariableSelectionNetwork(nn.Module):
    def __init__(self, num_features: int, hidden_size: int, dropout: float) -> None:
        super().__init__()
        self.feature_grns = nn.ModuleList(
            [GatedResidualNetwork(1, hidden_size, hidden_size, dropout) for _ in range(num_features)]
        )
        self.weight_grn = GatedResidualNetwork(num_features, hidden_size, num_features, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feature_embeddings = [grn(x[..., idx:idx + 1]) for idx, grn in enumerate(self.feature_grns)]
        stacked = torch.stack(feature_embeddings, dim=-2)
        weights = torch.softmax(self.weight_grn(x), dim=-1).unsqueeze(-1)
        return torch.sum(stacked * weights, dim=-2)


class PositionalEncoding(nn.Module):
    def __init__(self, hidden_size: int, max_len: int = 2048) -> None:
        super().__init__()
        position = torch.arange(max_len, dtype=torch.float32).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, hidden_size, 2, dtype=torch.float32) * (-math.log(10000.0) / hidden_size))
        pe = torch.zeros(max_len, hidden_size, dtype=torch.float32)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0), persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1)]


class TFTPVModel(nn.Module):
    def __init__(
        self,
        encoder_input_size: int,
        hidden_size: int,
        lstm_layers: int,
        attention_heads: int,
        dropout: float,
        prediction_length: int,
    ) -> None:
        super().__init__()
        self.prediction_length = prediction_length
        self.weather_vsn = VariableSelectionNetwork(encoder_input_size, hidden_size, dropout)
        self.pv_embed = GatedResidualNetwork(1, hidden_size, hidden_size, dropout)
        self.positional_encoding = PositionalEncoding(hidden_size)
        self.encoder_lstm = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0.0,
        )
        self.decoder_lstm = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0.0,
        )
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size,
            num_heads=attention_heads,
            dropout=dropout,
            batch_first=True,
        )
        self.post_attn = GatedResidualNetwork(hidden_size * 2, hidden_size, hidden_size, dropout)
        self.output_layer = nn.Sequential(
            GatedResidualNetwork(hidden_size, hidden_size, hidden_size, dropout),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, encoder_x: torch.Tensor, decoder_pv: torch.Tensor, decoder_weather: torch.Tensor) -> torch.Tensor:
        weather_context = self.positional_encoding(self.weather_vsn(encoder_x))
        encoder_out, encoder_state = self.encoder_lstm(weather_context)
        decoder_pv_context = self.pv_embed(decoder_pv[:, -self.prediction_length:, :])
        decoder_weather_context = self.weather_vsn(decoder_weather)
        decoder_context = self.positional_encoding(decoder_pv_context + decoder_weather_context)
        decoder_out, _ = self.decoder_lstm(decoder_context, encoder_state)
        attended, _ = self.attention(query=decoder_out, key=encoder_out, value=encoder_out)
        fused = self.post_attn(torch.cat([decoder_out, attended], dim=-1))
        return self.output_layer(fused)


class HanPVModelBundle:
    def __init__(
        self,
        package_dir: Path,
        config: HanPVConfig,
        encoder_scaler: StandardScaler1D,
        target_scaler: StandardScaler1D,
        pv_max: float,
        manifest: dict[str, Any],
    ) -> None:
        self.package_dir = package_dir
        self.config = config
        self.encoder_scaler = encoder_scaler
        self.target_scaler = target_scaler
        self.pv_max = pv_max
        self.manifest = manifest
        self.feature_engineer = FeatureEngineer()
        self.model = TFTPVModel(
            encoder_input_size=len(self.feature_engineer.encoder_features),
            hidden_size=config.hidden_size,
            lstm_layers=config.lstm_layers,
            attention_heads=config.attention_heads,
            dropout=config.dropout,
            prediction_length=config.prediction_length,
        )
        state = torch.load(package_dir / "best_model.pt", map_location="cpu", weights_only=True)
        self.model.load_state_dict(state)
        self.model.eval()

    @classmethod
    def load(cls, package_dir: str | Path) -> "HanPVModelBundle":
        package = Path(package_dir)
        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
        scalers = json.loads((package / "scalers.json").read_text(encoding="utf-8"))
        config = HanPVConfig(**manifest["config"])
        return cls(
            package_dir=package,
            config=config,
            encoder_scaler=StandardScaler1D.from_dict(scalers["encoder_scaler"]),
            target_scaler=StandardScaler1D.from_dict(scalers["target_scaler"]),
            pv_max=float(manifest["training"]["pv_max_mwh"]),
            manifest=manifest,
        )

    def predict_payload(self, payload: dict[str, Any], capacity_kwh: float | None = None) -> dict[str, Any]:
        base_date = pd.to_datetime(payload["base_date"])
        context_rows, context_mode = _context_weather_rows(payload, base_date, self.config.encoder_length)
        future_rows = payload.get("decoder_weather_24h") or payload.get("future_weather_24h") or payload.get("encoder_weather_24h")
        if not isinstance(future_rows, list) or len(future_rows) != self.config.prediction_length:
            raise ValueError("24 future weather rows are required")

        decoder_pv_rows = payload.get("decoder_pv_24h")
        if not isinstance(decoder_pv_rows, list) or len(decoder_pv_rows) != self.config.decoder_length:
            raise ValueError("24 decoder PV rows are required")

        context_end = base_date + timedelta(hours=23)
        context_timestamps = [
            context_end - timedelta(hours=self.config.encoder_length - 1 - idx)
            for idx in range(self.config.encoder_length)
        ]
        target_date = base_date + timedelta(days=1)
        future_timestamps = [target_date + timedelta(hours=idx) for idx in range(self.config.prediction_length)]

        context_frame = self.feature_engineer.build_inference_features(context_rows, context_timestamps)
        future_frame = self.feature_engineer.build_inference_features(future_rows, future_timestamps)
        encoder_values = context_frame[self.feature_engineer.encoder_features].to_numpy(dtype=np.float32)
        future_values = future_frame[self.feature_engineer.encoder_features].to_numpy(dtype=np.float32)
        scale_kwh = float(capacity_kwh) if capacity_kwh is not None and capacity_kwh > 0 else None
        pv_denominator = scale_kwh if scale_kwh is not None else self.pv_max
        decoder_pv = np.array(
            [_pv_value(row) / (pv_denominator + 1e-6) for row in decoder_pv_rows],
            dtype=np.float32,
        ).reshape(-1, 1)

        encoder_x = torch.tensor(self.encoder_scaler.transform(encoder_values), dtype=torch.float32).unsqueeze(0)
        decoder_weather = torch.tensor(self.encoder_scaler.transform(future_values), dtype=torch.float32).unsqueeze(0)
        decoder_pv_t = torch.tensor(self.target_scaler.transform(decoder_pv), dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            pred_scaled = self.model(encoder_x, decoder_pv_t, decoder_weather).cpu().numpy().reshape(-1, 1)
        pred_norm = self.target_scaler.inverse_transform(pred_scaled).reshape(-1)
        if scale_kwh is not None:
            pred_values = np.clip(pred_norm, 0.0, 1.0) * scale_kwh
            output_unit = "kWh"
            output_scaling = {
                "mode": "capacity_factor_to_requested_capacity",
                "requested_capacity_kwh": scale_kwh,
                "source_region_pv_max_mwh": self.pv_max,
            }
        else:
            pred_values = np.clip(pred_norm, 0.0, None) * self.pv_max
            output_unit = "MWh"
            output_scaling = {
                "mode": "raw_training_region_mwh",
                "source_region_pv_max_mwh": self.pv_max,
            }

        return {
            "target_date": target_date.strftime("%Y-%m-%d"),
            "predicted_pv_24h": [
                {"hour": hour, "pv_power": round(float(value), 6)}
                for hour, value in enumerate(pred_values.tolist())
            ],
            "context_mode": context_mode,
            "output_unit": output_unit,
            "output_scaling": output_scaling,
        }


def save_package(
    package_dir: Path,
    config: HanPVConfig,
    model: nn.Module,
    encoder_scaler: StandardScaler1D,
    target_scaler: StandardScaler1D,
    metrics: dict[str, float],
    pv_max: float,
    source_files: dict[str, str],
) -> None:
    package_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), package_dir / "best_model.pt")
    (package_dir / "scalers.json").write_text(
        json.dumps(
            {
                "encoder_scaler": encoder_scaler.to_dict(),
                "target_scaler": target_scaler.to_dict(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    manifest = {
        "model_id": package_dir.name,
        "owner": "han_mingu",
        "model_type": "tft_style_weather_encoder_pv_decoder",
        "config": asdict(config),
        "feature_order": FeatureEngineer().encoder_features,
        "required_runtime_files": ["best_model.pt", "scalers.json", "manifest.json"],
        "training": {
            "pv_max_mwh": pv_max,
            "source_files": source_files,
            "metrics": metrics,
        },
        "api_input": {
            "supports": ["encoder_weather_168h", "encoder_weather_24h repeated context fallback"],
            "requires": ["base_date", "decoder_pv_24h", "future weather 24h or encoder_weather_24h"],
        },
    }
    (package_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (package_dir / "config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")


def _first_numeric(row: dict[str, Any], aliases: list[str]) -> float:
    for alias in aliases:
        if alias in row and row[alias] is not None:
            try:
                value = float(row[alias])
            except (TypeError, ValueError):
                continue
            if value == value:
                return value
    raise ValueError(f"missing numeric weather feature: {aliases[0]}")


def _pv_value(row: Any) -> float:
    if isinstance(row, dict):
        for key in ["pv_power", "pv_forecast", "value", "실제발전량"]:
            if key in row:
                return max(0.0, float(row[key]))
    return max(0.0, float(row))


def _context_weather_rows(payload: dict[str, Any], base_date: pd.Timestamp, encoder_length: int) -> tuple[list[dict[str, Any]], str]:
    rows = payload.get("encoder_weather_168h")
    if isinstance(rows, list) and len(rows) == encoder_length:
        return rows, "provided_168h"
    rows = payload.get("encoder_weather_24h")
    if isinstance(rows, list) and len(rows) == 24:
        repeated = []
        for _ in range(encoder_length // 24):
            repeated.extend(rows)
        return repeated[-encoder_length:], "repeated_24h_weather"
    raise ValueError("encoder_weather_168h or encoder_weather_24h is required")
