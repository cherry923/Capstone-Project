from __future__ import annotations

from datetime import timedelta
from typing import Any, TYPE_CHECKING

from app import responses
from app.settings import DEFAULT_PV_CAPACITY_KWH, TEAM_PV_ENABLED, TEAM_PV_MODEL_PACKAGE_DIR
from app.validation import as_number, get_number_with_aliases, missing, parse_yyyy_mm_dd

if TYPE_CHECKING:
    from app.team_pv.runtime import HanPVModelBundle


WEATHER_ALIASES = {
    "hour": ["hour"],
    "temperature": ["temperature", "temp"],
    "rain": ["rain", "precipitation", "rainfall"],
    "humidity": ["humidity"],
    "snow": ["snow", "snowfall"],
    "cloud": ["cloud", "cloud_cover"],
    "duration": ["duration", "sunshine_duration"],
    "radiation": ["radiation", "irradiance", "solar_radiation"],
    "day": ["day", "is_holiday"],
}


class PVPredictionService:
    """Document-compatible PV prediction endpoint.

    The team TFT notebook does not currently provide deployable weights in this
    repository. This service keeps the API contract stable and exposes a
    deterministic shadow predictor until a real TFT/Transformer artifact is
    exported.
    """

    _team_bundle: "HanPVModelBundle | None" = None
    _team_load_error: str | None = None

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("request_id")
        missing_field = missing(
            payload,
            ["request_id", "station_id", "base_date", "encoder_weather_24h", "decoder_pv_24h"],
        )
        if missing_field:
            return responses.error(
                request_id, responses.MISSING_REQUIRED_FIELD, f"missing field: {missing_field}"
            )

        base_date = parse_yyyy_mm_dd(payload["base_date"])
        if base_date is None:
            return responses.error(request_id, responses.INVALID_DATE_FORMAT, "base_date must be YYYY-MM-DD")

        weather = payload["encoder_weather_24h"]
        pv_history = payload["decoder_pv_24h"]
        if not isinstance(weather, list) or not isinstance(pv_history, list):
            return responses.error(request_id, responses.INVALID_ARRAY_LENGTH, "weather and pv arrays are required")
        if len(weather) != 24 or len(pv_history) != 24:
            return responses.error(request_id, responses.INVALID_ARRAY_LENGTH, "24 hourly records are required")

        capacity = as_number(payload.get("capacity_kwh", DEFAULT_PV_CAPACITY_KWH))
        if capacity is None or capacity <= 0:
            return responses.error(request_id, responses.INVALID_INPUT_VALUE, "capacity_kwh must be > 0")

        team_prediction = self._try_team_model(payload, capacity)
        if team_prediction is not None:
            return team_prediction

        target_date = (base_date + timedelta(days=1)).strftime("%Y-%m-%d")
        predicted = []
        previous_values: list[float] = []

        for idx, (weather_row, pv_row) in enumerate(zip(weather, pv_history, strict=True)):
            if not isinstance(weather_row, dict) or not isinstance(pv_row, dict):
                return responses.error(request_id, responses.INSUFFICIENT_INPUT_DATA, "hourly rows must be objects")

            hour = get_number_with_aliases(weather_row, WEATHER_ALIASES["hour"])
            if hour is None or int(hour) != idx:
                return responses.error(request_id, responses.INVALID_INPUT_VALUE, "weather hour must be 0..23 in order")

            features: dict[str, float] = {}
            for feature, aliases in WEATHER_ALIASES.items():
                value = get_number_with_aliases(weather_row, aliases)
                if value is None:
                    return responses.error(
                        request_id, responses.INSUFFICIENT_INPUT_DATA, f"missing weather feature: {feature}"
                    )
                features[feature] = value

            pv_power = as_number(pv_row.get("pv_power"))
            if pv_power is None:
                return responses.error(request_id, responses.INSUFFICIENT_INPUT_DATA, "missing pv_power")
            if pv_power < 0:
                return responses.error(request_id, responses.INVALID_INPUT_VALUE, "pv_power must be >= 0")
            previous_values.append(pv_power)

            prediction = self._shadow_predict_hour(features, pv_power, capacity)
            predicted.append({"hour": idx, "pv_power": prediction})

        return responses.ok(
            request_id,
            {
                "station_id": payload["station_id"],
                "requested_region": self._requested_region(payload),
                "loaded_region": None,
                "region_model_status": "TEAM_MODEL_UNAVAILABLE",
                "base_date": payload["base_date"],
                "target_date": target_date,
                "predicted_pv_24h": predicted,
                "output_unit": "kWh",
                "output_scaling": {
                    "mode": "shadow_capacity_kwh",
                    "requested_capacity_kwh": capacity,
                },
                "model_name": "team_tft_shadow_adapter",
                "model_status": "WEIGHTS_NOT_EXPORTED",
                "team_model_error": self._team_load_error,
                "note": "API-compatible shadow predictor based on team TFT input features; replace with exported TFT weights when available.",
            },
        )

    def _try_team_model(self, payload: dict[str, Any], capacity_kwh: float) -> dict[str, Any] | None:
        if not TEAM_PV_ENABLED:
            self._team_load_error = "TEAM_PV_ENABLED is disabled"
            return None
        if not TEAM_PV_MODEL_PACKAGE_DIR.exists():
            self._team_load_error = f"PV model package not found: {TEAM_PV_MODEL_PACKAGE_DIR}"
            return None

        try:
            bundle = self._load_team_bundle()
            result = bundle.predict_payload(payload, capacity_kwh=capacity_kwh)
        except Exception as exc:
            self._team_load_error = str(exc)
            return None

        requested_region = self._requested_region(payload)
        loaded_region = self._bundle_region(bundle)
        self._team_load_error = None
        return responses.ok(
            payload.get("request_id"),
            {
                "station_id": payload["station_id"],
                "requested_region": requested_region,
                "loaded_region": loaded_region,
                "region_model_status": self._region_model_status(requested_region, loaded_region),
                "base_date": payload["base_date"],
                "target_date": result["target_date"],
                "predicted_pv_24h": result["predicted_pv_24h"],
                "output_unit": result.get("output_unit", "kWh"),
                "output_scaling": result.get("output_scaling"),
                "model_name": bundle.manifest.get("model_id", "han_tft_pv_incheon"),
                "model_status": "TEAM_TFT_PV_LOADED",
                "context_mode": result["context_mode"],
                "metrics": bundle.manifest.get("training", {}).get("metrics"),
                "metrics_status": bundle.manifest.get("training", {}).get("metrics_status"),
                "active_weight": bundle.manifest.get("active_weight"),
                "note": "Han Mingu TFT-style PV package loaded from local best_model.pt/scalers/manifest.",
            },
        )

    def _load_team_bundle(self) -> HanPVModelBundle:
        if self._team_bundle is None:
            from app.team_pv.runtime import HanPVModelBundle

            self._team_bundle = HanPVModelBundle.load(TEAM_PV_MODEL_PACKAGE_DIR)
        return self._team_bundle

    def _requested_region(self, payload: dict[str, Any]) -> str | None:
        for key in ("pv_region", "region", "station_region"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _bundle_region(self, bundle: HanPVModelBundle) -> str | None:
        config = bundle.manifest.get("config", {})
        if not isinstance(config, dict):
            return None
        value = config.get("station_name")
        return value if isinstance(value, str) and value.strip() else None

    def _region_model_status(self, requested_region: str | None, loaded_region: str | None) -> str:
        if requested_region is None:
            return "REGION_UNSPECIFIED"
        if loaded_region is None:
            return "LOADED_MODEL_REGION_UNKNOWN"
        if requested_region == loaded_region:
            return "REGION_MATCHED"
        return "FALLBACK_TO_LOADED_REGION_MODEL"

    def _shadow_predict_hour(self, weather: dict[str, float], lag24_pv: float, capacity: float) -> float:
        hour = int(weather["hour"])
        daylight = max(0.0, __import__("math").sin(__import__("math").pi * (hour - 6) / 12.0))
        radiation = max(0.0, weather["radiation"])
        duration = max(0.0, weather["duration"])
        cloud = max(0.0, weather["cloud"])
        rain = max(0.0, weather["rain"])
        snow = max(0.0, weather["snow"])
        temp = weather["temperature"]

        radiation_signal = min(1.0, radiation / 4.0)
        sunshine_signal = min(1.0, duration)
        cloud_penalty = 1.0 - min(0.75, cloud / 13.0)
        precipitation_penalty = 1.0 - min(0.35, (rain + snow) / 30.0)
        temp_penalty = 1.0 - min(0.15, abs(temp - 25.0) / 120.0)
        weather_power = capacity * daylight * max(radiation_signal, sunshine_signal * 0.55)
        weather_power *= cloud_penalty * precipitation_penalty * temp_penalty

        blended = 0.75 * weather_power + 0.25 * lag24_pv
        return round(max(0.0, min(capacity, blended)), 6)
