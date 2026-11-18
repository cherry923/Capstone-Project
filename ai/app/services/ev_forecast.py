from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app import responses
from app.settings import EV_SAC_PAYLOAD_PATH
from app.validation import as_number


class EVDemandForecastService:
    """Load the current EV 24h forecast artifact for SAC/share-plan input."""

    def __init__(self, payload_path: Path = EV_SAC_PAYLOAD_PATH) -> None:
        self.payload_path = payload_path

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("request_id")
        if not self.payload_path.exists():
            return responses.error(
                request_id,
                responses.MODEL_INFERENCE_FAILED,
                f"EV SAC payload not found: {self.payload_path}",
            )

        scale = as_number(payload.get("scale", 1.0))
        if scale is None or scale < 0:
            return responses.error(request_id, responses.INVALID_INPUT_VALUE, "scale must be >= 0")

        with self.payload_path.open("r", encoding="utf-8") as handle:
            package = json.load(handle)

        forecast = []
        for hour, mean, p10, p50, p90 in zip(
            package["horizon_hours"],
            package["ev_demand_kwh_mean"],
            package["ev_demand_kwh_p10"],
            package["ev_demand_kwh_p50"],
            package["ev_demand_kwh_p90"],
            strict=True,
        ):
            forecast.append(
                {
                    "hour": int(hour),
                    "ev_demand_mean": float(mean) * scale,
                    "ev_demand_p10": float(p10) * scale,
                    "ev_demand_p50": float(p50) * scale,
                    "ev_demand_p90": float(p90) * scale,
                }
            )

        return responses.ok(
            request_id,
            {
                "station_id": payload.get("station_id"),
                "aggregate_key": package.get("aggregate_key"),
                "base_datetime": package.get("base_datetime"),
                "model_name": package.get("model_name"),
                "source_package": package.get("source_package"),
                "horizon_hours": package.get("horizon_hours"),
                "forecast_24h": forecast,
                "note": package.get("note"),
            },
        )

