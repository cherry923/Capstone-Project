from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app import responses
from app.services.decision import LowerDecisionService, UpperDecisionService
from app.services.ev_forecast import EVDemandForecastService
from app.services.pv_prediction import PVPredictionService
from app.services.team_sac_runtime import TeamSACDecisionRuntime, TeamSACRuntimeUnavailable
from app.settings import (
    DEFAULT_ESS_CAPACITY_KWH,
    DEFAULT_ESS_POWER_LIMIT_KWH,
    EV_SAC_PAYLOAD_PATH,
    EV_STRICT_MISMATCH_DAYS,
    EV_STRICT_TARGET_DATE,
    REGIONAL_VIRTUAL_HUB_SPEC,
    SOC_MIN,
    TEAM_SAC_MODEL_PACKAGE_DIR,
)
from app.validation import as_number, parse_yyyy_mm_dd


TEAM_STATION_COUNT = 3
HORIZON_HOURS = 24
DEFAULT_TOU_LOW = 84.5
DEFAULT_TOU_MID = 111.9
DEFAULT_TOU_HIGH = 174.0
TEAM_SOC_MIN = 0.1
TEAM_SOC_MAX = 0.9


@dataclass
class ForecastStation:
    station_id: int | str
    init_soc: float
    pv_forecast_24h: list[float]
    demand_forecast_24h: list[float]
    pv_actual_24h: list[float]
    demand_actual_24h: list[float]
    ess_capacity_kwh: float
    ess_power_limit_kwh: float
    demand_p90_24h: list[float] | None = None


@dataclass
class FlowInputs:
    target_date: str
    station_ids: list[int | str]
    init_soc: list[float]
    tou_24h: list[float]
    stations: list[ForecastStation]
    forecast_source: dict[str, Any]
    ev_scale_used: float = 1.0
    scale_source: str = "default"
    normalized_demand_weights: list[float] = field(default_factory=list)
    normalized_pv_scales: list[float] = field(default_factory=list)
    aggregate_input_source: str = "ev_service"
    scenario_mode: str = "single_charger"


@dataclass
class PVForecastSelection:
    values: list[float] | None
    source: str
    model_name: str | None = None
    model_status: str | None = None
    fallback_reason: str | None = None
    requested_region: str | None = None
    loaded_region: str | None = None
    region_model_status: str | None = None


class DispatchFlowService:
    """End-to-end PV/EV forecast to upper/lower decision command flow."""

    def __init__(self) -> None:
        self.ev = EVDemandForecastService()
        self.pv = PVPredictionService()
        self.upper = UpperDecisionService()
        self.lower = LowerDecisionService()
        self.team_runtime = TeamSACDecisionRuntime()

    def generate_dispatch_24h(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("request_id")

        target_date = payload.get("target_date", "demo_day")
        if target_date != "demo_day" and parse_yyyy_mm_dd(target_date) is None:
            return responses.error(request_id, responses.INVALID_DATE_FORMAT, "target_date must be YYYY-MM-DD")

        try:
            flow_inputs = self._build_inputs(payload)
        except ValueError as exc:
            return responses.error(request_id, responses.INVALID_INPUT_VALUE, str(exc))

        ev_detail = flow_inputs.forecast_source.get("ev_detail", {})
        should_reject, reject_reason = self._ev_strict_check(ev_detail)
        if should_reject:
            return responses.error(request_id, responses.INVALID_INPUT_VALUE, reject_reason)

        warnings: list[str] = []
        warning = self._historical_warning(ev_detail)
        if warning is not None:
            warnings.append(warning)

        runtime_error: str | None = None
        prefer_team_model = payload.get("use_team_model", True) is not False
        if prefer_team_model:
            try:
                result = self.team_runtime.run(self._to_team_day_data(flow_inputs))
                commands = self._rows_to_commands(result.rows, flow_inputs)
                algo = result.manifest.get("algorithm", {})
                if algo.get("upper_algo") == "DEFAULT" and algo.get("lower_algo") == "DEFAULT" and algo.get("uses_safety_shield"):
                    status_tag = "TEAM_FALLBACK_SHIELD_LOADED"
                elif algo.get("upper_algo") in {"SOFT_PEAK_MILP", "QUANTILE_SAFETY_MILP"} and algo.get("lower_algo") == "DEFAULT" and algo.get("uses_safety_shield"):
                    status_tag = "TEAM_SHARE_MILP_SHIELD_LOADED"
                else:
                    status_tag = "TEAM_MILP_PI_SAC_LOADED"
                model_info = self._model_info_from_manifest(result.manifest, status_tag)
            except Exception as exc:
                runtime_error = str(exc)
                commands = self._fallback_commands(flow_inputs)
                model_info = {
                    "model_name": "upper_lower_rule_fallback",
                    "model_status": "FALLBACK_AFTER_TEAM_MODEL_UNAVAILABLE",
                    "fallback_reason": runtime_error,
                }
        else:
            commands = self._fallback_commands(flow_inputs)
            model_info = {
                "model_name": "upper_lower_rule_fallback",
                "model_status": "FALLBACK_REQUESTED",
            }

        return responses.ok(
            request_id,
            {
                "target_date": flow_inputs.target_date,
                "horizon_hours": list(range(HORIZON_HOURS)),
                "station_count": len(flow_inputs.stations),
                "forecasts": self._forecast_summary(flow_inputs),
                "dispatch": {
                    "commands": commands,
                    "share_plan_24h": self._share_plan_24h(commands),
                    "summary": self._summary(commands),
                },
                "validity": self._scenario_validity(commands, model_info.get("model_status")),
                "model": model_info,
                "scenario": {
                    "scenario_mode": flow_inputs.scenario_mode,
                    "ev_scale_used": flow_inputs.ev_scale_used,
                    "scale_source": flow_inputs.scale_source,
                    "normalized_demand_weights": flow_inputs.normalized_demand_weights,
                    "normalized_pv_scales": flow_inputs.normalized_pv_scales,
                    "aggregate_input_source": flow_inputs.aggregate_input_source,
                    "station_spec": (
                        REGIONAL_VIRTUAL_HUB_SPEC
                        if flow_inputs.scenario_mode == "regional_virtual_hub"
                        else "single_charger (manifest shield_config)"
                    ),
                },
                "warnings": warnings,
                "flow": [
                    "pv_prediction",
                    "ev_prediction",
                    "upper_share_decision",
                    "lower_station_policy",
                    "station_command_response",
                ],
                "notes": [
                    "PV uses request-provided station values when present, then Han's packaged TFT PV model when top-level PV inputs are present, otherwise a daylight fallback.",
                    "EV uses the current local 24h probabilistic demand artifact and splits it across the 3-station decision model unless station-level demand arrays are supplied.",
                    "For future dispatch, pv_actual/demand_actual are set to forecasts unless explicit actual arrays are supplied.",
                ],
            },
        )

    def _ev_payload_metadata(self, target_date: str) -> dict[str, Any]:
        """Read the EV SAC payload header and compute target-date mismatch info.

        The production EV payload is a fixed historical scenario. When the
        caller asks for a future target_date (typical for dispatch demos), the
        forecast is not a real prediction for that date. This metadata makes
        that explicit so downstream API consumers do not silently treat the
        payload as a live forecast.
        """
        detail: dict[str, Any] = {
            "mode": "historical_fixed_payload",
            "payload_path": str(EV_SAC_PAYLOAD_PATH),
        }
        if not EV_SAC_PAYLOAD_PATH.exists():
            detail["historical_scenario"] = True
            detail["payload_available"] = False
            return detail
        try:
            with EV_SAC_PAYLOAD_PATH.open("r", encoding="utf-8") as handle:
                package = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            detail["historical_scenario"] = True
            detail["payload_available"] = False
            detail["read_error"] = str(exc)
            return detail

        base_dt_raw = package.get("base_datetime")
        detail["payload_base_datetime"] = base_dt_raw
        detail["payload_model_name"] = package.get("model_name")
        detail["payload_aggregate_key"] = package.get("aggregate_key")
        detail["payload_available"] = True
        detail["historical_scenario"] = True
        detail["requested_target_date"] = target_date

        payload_date = self._parse_payload_date(base_dt_raw)
        target_dt = parse_yyyy_mm_dd(target_date) if target_date and target_date != "demo_day" else None
        target_date_obj = target_dt.date() if target_dt is not None else None
        if payload_date is not None and target_date_obj is not None:
            mismatch = (target_date_obj - payload_date).days
            detail["target_date_mismatch_days"] = int(mismatch)
            detail["payload_base_date"] = payload_date.isoformat()
        else:
            detail["target_date_mismatch_days"] = None
        return detail

    @staticmethod
    def _parse_payload_date(value: Any) -> date | None:
        if not isinstance(value, str):
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None

    def _ev_strict_check(self, ev_detail: dict[str, Any]) -> tuple[bool, str | None]:
        """Return (should_reject, reason) when strict-target-date mode is on."""
        if not EV_STRICT_TARGET_DATE:
            return False, None
        mismatch = ev_detail.get("target_date_mismatch_days")
        if mismatch is None:
            return False, None
        if abs(int(mismatch)) <= EV_STRICT_MISMATCH_DAYS:
            return False, None
        return True, (
            f"target_date is {mismatch} days away from EV payload base_datetime "
            f"({ev_detail.get('payload_base_datetime')}); exceeds EV_STRICT_MISMATCH_DAYS="
            f"{EV_STRICT_MISMATCH_DAYS}"
        )

    @staticmethod
    def _historical_warning(ev_detail: dict[str, Any]) -> str | None:
        if ev_detail.get("payload_available") is False:
            return None
        mismatch = ev_detail.get("target_date_mismatch_days")
        if mismatch is None:
            return (
                "EV demand forecast is served from a fixed historical payload."
            )
        return (
            "EV demand forecast is served from a fixed historical payload "
            f"(base_datetime={ev_detail.get('payload_base_datetime')}); the requested "
            f"target_date is {mismatch} days away. Numbers are an integration scenario, "
            "not a real forecast for that date."
        )

    def _build_inputs(self, payload: dict[str, Any]) -> FlowInputs:
        target_date = payload.get("target_date", "demo_day")
        station_payloads = payload.get("stations")
        if station_payloads is None:
            station_payloads = [{"station_id": index + 1} for index in range(TEAM_STATION_COUNT)]
        if not isinstance(station_payloads, list):
            raise ValueError("stations must be an array when provided")
        if len(station_payloads) > TEAM_STATION_COUNT:
            raise ValueError("the received PI-SAC package supports exactly 3 stations")

        station_payloads = list(station_payloads)
        while len(station_payloads) < TEAM_STATION_COUNT:
            station_payloads.append({"station_id": len(station_payloads) + 1})

        tou_24h = self._extract_24_values(payload.get("tou_24h"), ["tou", "tou_price", "value"], self._default_tou())
        if any(value < 0 for value in tou_24h):
            raise ValueError("tou_24h values must be >= 0")

        aggregate_ev, aggregate_ev_p90, aggregate_input_source = self._aggregate_ev(payload)
        # Default scenario: the production EV payload is aggregate (jeju_total), which only makes
        # physical sense against the regional_virtual_hub spec. Defaulting an aggregate payload to
        # single_charger would expose huge peak violations on a plain call, so auto-select the hub
        # scenario unless the caller supplies explicit station-level demand or overrides the mode.
        _station_demand_keys = ("demand_forecast_24h", "ev_demand_24h", "demand_actual_24h")
        explicit_station_demand = any(
            isinstance(sp, dict) and any(k in sp for k in _station_demand_keys)
            for sp in payload.get("stations", []) or []
        )
        default_scenario = (
            "single_charger" if explicit_station_demand else "regional_virtual_hub"
        )
        raw_mode = payload.get("scenario_mode")
        scenario_mode = str(raw_mode) if raw_mode else default_scenario  # treat null/"" as unset
        if scenario_mode not in ("single_charger", "regional_virtual_hub"):
            raise ValueError("scenario_mode must be 'single_charger' or 'regional_virtual_hub'")
        if "ev_scale" in payload:
            ev_scale_used = float(payload.get("ev_scale", 1.0))
            scale_source = "request_ev_scale"
        elif scenario_mode == "regional_virtual_hub":
            # Regional hub uses the full aggregate demand against scaled-up station physics.
            ev_scale_used = 1.0
            scale_source = "regional_aggregate"
        else:
            ev_scale_used = 1.0
            scale_source = "default"
        demand_weights = self._normalized_weights(payload.get("station_demand_weights"), [0.34, 0.36, 0.30])
        pv_scales = self._normalized_pv_scales(payload.get("station_pv_scales"), [1.0, 0.85, 1.2])
        default_station_pv_capacity = (
            REGIONAL_VIRTUAL_HUB_SPEC["pv_capacity_kwh"]
            if scenario_mode == "regional_virtual_hub"
            else 100.0
        )
        top_level_pv_capacity = self._number_or_default(
            payload.get("pv_capacity_kwh"),
            default_station_pv_capacity,
        )
        top_level_pv_forecast = self._top_level_pv_forecast(payload, top_level_pv_capacity)

        explicit_init_soc = self._optional_float_array(payload.get("init_soc"), "init_soc")
        if explicit_init_soc is not None and len(explicit_init_soc) != TEAM_STATION_COUNT:
            raise ValueError("init_soc must have 3 values")

        stations: list[ForecastStation] = []
        station_pv_sources: list[dict[str, Any]] = []
        for index, station_payload in enumerate(station_payloads):
            if not isinstance(station_payload, dict):
                raise ValueError(f"station[{index}] must be an object")

            station_id = station_payload.get("station_id", index + 1)
            init_soc = (
                explicit_init_soc[index]
                if explicit_init_soc is not None
                else self._number_or_default(station_payload.get("ess_soc"), 0.5)
            )
            if not 0.0 <= init_soc <= 1.0:
                raise ValueError("ess_soc/init_soc must be between 0 and 1")

            capacity = self._number_or_default(station_payload.get("pv_capacity_kwh"), default_station_pv_capacity)
            station_pv_input = self._first_present(station_payload, "pv_forecast_24h", "predicted_pv_24h")
            if top_level_pv_forecast.values is None:
                pv_default = self._default_pv(capacity * pv_scales[index])
                default_pv_source = "daylight_fallback"
            else:
                pv_default = [value * pv_scales[index] for value in top_level_pv_forecast.values]
                default_pv_source = top_level_pv_forecast.source
            pv_forecast = self._extract_24_values(
                station_pv_input,
                ["pv_power", "pv_forecast", "value"],
                pv_default,
            )
            station_pv_source = "station_payload" if station_pv_input is not None else default_pv_source
            demand_default = [value * demand_weights[index] for value in aggregate_ev]
            station_demand_input = self._first_present(station_payload, "demand_forecast_24h", "ev_demand_24h")
            demand_forecast = self._extract_24_values(
                station_demand_input,
                ["ev_demand", "demand_forecast", "ev_demand_p50", "value"],
                demand_default,
            )
            # demand_p90 must share the demand_forecast's provenance. If the station supplied its own
            # demand, the aggregate p90 is meaningless for it — use an explicit station p90 if given,
            # otherwise None so the runtime falls back to that station's own p50-based margin. Only a
            # default (aggregate-weighted) demand inherits the aggregate-weighted p90.
            if station_demand_input is not None:
                explicit_p90 = station_payload.get("demand_p90_24h")
                demand_p90 = (
                    self._extract_24_values(explicit_p90, ["demand_p90", "ev_demand_p90", "value"], demand_forecast)
                    if explicit_p90 is not None
                    else None
                )
            else:
                demand_p90 = (
                    [value * demand_weights[index] for value in aggregate_ev_p90]
                    if aggregate_ev_p90 is not None
                    else None
                )
            pv_actual = self._extract_24_values(
                station_payload.get("pv_actual_24h"),
                ["pv_actual", "pv_power", "value"],
                pv_forecast,
            )
            demand_actual = self._extract_24_values(
                station_payload.get("demand_actual_24h"),
                ["demand_actual", "ev_demand", "value"],
                demand_forecast,
            )

            for label, values in {
                "pv_forecast_24h": pv_forecast,
                "demand_forecast_24h": demand_forecast,
                "pv_actual_24h": pv_actual,
                "demand_actual_24h": demand_actual,
            }.items():
                if any(value < 0 for value in values):
                    raise ValueError(f"{label} values must be >= 0")

            stations.append(
                ForecastStation(
                    station_id=station_id,
                    init_soc=init_soc,
                    pv_forecast_24h=pv_forecast,
                    demand_forecast_24h=demand_forecast,
                    pv_actual_24h=pv_actual,
                    demand_actual_24h=demand_actual,
                    ess_capacity_kwh=self._number_or_default(
                        station_payload.get("ess_capacity_kwh"), DEFAULT_ESS_CAPACITY_KWH
                    ),
                    ess_power_limit_kwh=self._number_or_default(
                        station_payload.get("ess_power_limit_kwh"), DEFAULT_ESS_POWER_LIMIT_KWH
                    ),
                    demand_p90_24h=demand_p90,
                )
            )
            station_pv_sources.append({"station_id": station_id, "source": station_pv_source})

        pv_source_values = sorted({row["source"] for row in station_pv_sources})
        pv_source = pv_source_values[0] if len(pv_source_values) == 1 else "mixed"

        ev_detail = self._ev_payload_metadata(target_date)
        return FlowInputs(
            target_date=target_date,
            station_ids=[station.station_id for station in stations],
            init_soc=[station.init_soc for station in stations],
            tou_24h=tou_24h,
            stations=stations,
            forecast_source={
                "pv": pv_source,
                "pv_detail": {
                    "network_candidate": top_level_pv_forecast.source,
                    "network_model_name": top_level_pv_forecast.model_name,
                    "network_model_status": top_level_pv_forecast.model_status,
                    "fallback_reason": top_level_pv_forecast.fallback_reason,
                    "requested_region": top_level_pv_forecast.requested_region,
                    "loaded_region": top_level_pv_forecast.loaded_region,
                    "region_model_status": top_level_pv_forecast.region_model_status,
                    "station_sources": station_pv_sources,
                },
                "ev": str(EV_SAC_PAYLOAD_PATH),
                "ev_detail": ev_detail,
                "team_decision_model": str(TEAM_SAC_MODEL_PACKAGE_DIR),
            },
            ev_scale_used=ev_scale_used,
            scale_source=scale_source,
            normalized_demand_weights=list(demand_weights),
            normalized_pv_scales=list(pv_scales),
            aggregate_input_source=aggregate_input_source,
            scenario_mode=scenario_mode,
        )

    def _to_team_day_data(self, flow_inputs: FlowInputs) -> dict[str, Any]:
        import numpy as np

        day_data: dict[str, Any] = {
            "date": flow_inputs.target_date,
            "tou": np.array(flow_inputs.tou_24h, dtype=np.float32),
            "init_soc": np.array(flow_inputs.init_soc, dtype=np.float32),
            "stations": [
                {
                    "pv_forecast": np.array(station.pv_forecast_24h, dtype=np.float32),
                    "demand_forecast": np.array(station.demand_forecast_24h, dtype=np.float32),
                    "pv_actual": np.array(station.pv_actual_24h, dtype=np.float32),
                    "demand_actual": np.array(station.demand_actual_24h, dtype=np.float32),
                    **(
                        {"demand_p90": np.array(station.demand_p90_24h, dtype=np.float32)}
                        if station.demand_p90_24h is not None
                        else {}
                    ),
                }
                for station in flow_inputs.stations
            ],
        }
        if flow_inputs.scenario_mode == "regional_virtual_hub":
            day_data["station_config"], day_data["shield_config_override"] = self._regional_hub_configs()
            day_data["share_abs_max_kwh"] = REGIONAL_VIRTUAL_HUB_SPEC["share_abs_max_kwh"]
        return day_data

    @staticmethod
    def _regional_hub_configs():
        """Build scaled-up station physics + shield for the regional_virtual_hub scenario.

        Injected through day_data (not by mutating the global ST_CFG) so concurrent
        single_charger requests are unaffected. Spec validated by probe_regional_hub.py.
        """
        from app.team_runtime.evcs_runtime import StationConfig
        from app.team_runtime.safety_shield import ShieldConfig

        spec = REGIONAL_VIRTUAL_HUB_SPEC
        station_config = StationConfig(
            pv_capacity_kwh=spec["pv_capacity_kwh"],
            ess_capacity_kwh=spec["ess_capacity_kwh"],
            ess_max_ratio=spec["ess_max_ratio"],
            soc_min=spec["soc_min"],
            soc_max=spec["soc_max"],
            vmax_kwh=spec["vmax_kwh"],
            peak_limit_kwh=spec["peak_limit_kwh"],
        )
        shield_override = ShieldConfig(
            peak_limit_kwh=spec["peak_limit_kwh"],
            soc_min=spec["soc_min"],
            soc_max=spec["soc_max"],
            ess_max_ratio_per_step=spec["ess_max_ratio"],
            ess_capacity_kwh=spec["ess_capacity_kwh"],
            future_horizon_hours=6,
        )
        return station_config, shield_override

    def _rows_to_commands(self, rows: list[dict[str, Any]], flow_inputs: FlowInputs) -> list[dict[str, Any]]:
        commands = []
        for row in rows:
            station_index = int(row["station"])
            raw_a_ess = float(row["a_ess"])
            soc_before = float(row["soc_before"])
            safe_a_ess = self._safe_ess_action(raw_a_ess, soc_before)
            safety_adjusted = abs(safe_a_ess - raw_a_ess) > 1e-9
            commands.append(
                {
                    "hour": int(row["t"]),
                    "station_id": flow_inputs.station_ids[station_index],
                    "share_energy_kwh": round(float(row["share"]), 6),
                    "ess_action": round(safe_a_ess, 6),
                    "raw_ess_action": round(raw_a_ess, 6),
                    "pv_priority": round(float(row["a_pv"]), 6),
                    "soc_before": round(soc_before, 6),
                    "soc_after": round(min(TEAM_SOC_MAX, max(TEAM_SOC_MIN, soc_before + safe_a_ess)), 6),
                    "model_soc_after": round(float(row["soc_after"]), 6),
                    "grid_total_kwh": round(float(row["grid_total_kwh"]), 6),
                    "grid_cost": round(float(row["grid_cost"]), 6),
                    "self_supply_kwh": round(float(row["self_supply_kwh"]), 6),
                    "loss_kwh": round(float(row["loss_kwh"]), 6),
                    "peak_violation": round(float(row["peak_violation"]), 6),
                    "soc_violation": round(float(row["soc_violation"]), 6),
                    "objective_reward": round(float(row["objective_reward"]), 6),
                    "safety_adjusted": safety_adjusted,
                    "shield_fired": list(row.get("shield_fired", [])),
                    "shield_diag": {k: round(float(v), 4) for k, v in row.get("shield_diag", {}).items()},
                    "command": self._command_label(safe_a_ess, float(row["a_pv"])),
                }
            )
        return commands

    def _fallback_commands(self, flow_inputs: FlowInputs) -> list[dict[str, Any]]:
        soc = list(flow_inputs.init_soc)
        commands = []

        for hour in range(HORIZON_HOURS):
            stations_now = [
                {
                    "station_id": station.station_id,
                    "ess_soc": soc[index],
                    "pv_power": station.pv_forecast_24h[hour],
                    "ev_demand": station.demand_forecast_24h[hour],
                    "tou_price": flow_inputs.tou_24h[hour],
                    "ess_capacity_kwh": station.ess_capacity_kwh,
                    "ess_power_limit_kwh": station.ess_power_limit_kwh,
                }
                for index, station in enumerate(flow_inputs.stations)
            ]
            share_response = self.upper.generate_share_plan({"time": hour, "stations": stations_now})
            share_plan = share_response["data"]["share_plan"] if share_response["code"] == responses.SUCCESS else []
            share_by_station = {row["station_id"]: row["share_energy"] for row in share_plan}

            for index, station in enumerate(flow_inputs.stations):
                share = float(share_by_station.get(station.station_id, 0.0))
                local_response = self.lower.generate_local_policy(
                    {
                        "station_id": station.station_id,
                        "time": hour,
                        "ess_soc": soc[index],
                        "pv_power": station.pv_forecast_24h[hour],
                        "ev_demand": station.demand_forecast_24h[hour],
                        "tou_price": flow_inputs.tou_24h[hour],
                        "share_energy": share,
                        "ess_capacity_kwh": station.ess_capacity_kwh,
                        "ess_power_limit_kwh": station.ess_power_limit_kwh,
                    }
                )
                policy = local_response["data"] if local_response["code"] == responses.SUCCESS else {"a_ess": 0.0, "a_pv": 1.0}
                a_ess = float(policy["a_ess"])
                a_pv = float(policy["a_pv"])
                soc_before = soc[index]
                soc[index] = min(1.0, max(SOC_MIN, soc[index] + a_ess))
                grid_total = self._fallback_grid(
                    pv=station.pv_forecast_24h[hour],
                    demand=station.demand_forecast_24h[hour],
                    share=share,
                    a_ess=a_ess,
                    ess_capacity=station.ess_capacity_kwh,
                )
                commands.append(
                    {
                        "hour": hour,
                        "station_id": station.station_id,
                        "share_energy_kwh": round(share, 6),
                        "ess_action": round(a_ess, 6),
                        "pv_priority": round(a_pv, 6),
                        "soc_before": round(soc_before, 6),
                        "soc_after": round(soc[index], 6),
                        "grid_total_kwh": round(grid_total, 6),
                        "grid_cost": round(grid_total * flow_inputs.tou_24h[hour], 6),
                        "self_supply_kwh": round(min(station.pv_forecast_24h[hour], station.demand_forecast_24h[hour]), 6),
                        "loss_kwh": 0.0,
                        "peak_violation": 0.0,
                        "soc_violation": 0.0,
                        "objective_reward": 0.0,
                        "command": self._command_label(a_ess, a_pv),
                    }
                )

        return commands

    def _forecast_summary(self, flow_inputs: FlowInputs) -> dict[str, Any]:
        return {
            "source": flow_inputs.forecast_source,
            "tou_24h": [round(value, 6) for value in flow_inputs.tou_24h],
            "stations": [
                {
                    "station_id": station.station_id,
                    "init_soc": round(station.init_soc, 6),
                    "pv_forecast_24h": [round(value, 6) for value in station.pv_forecast_24h],
                    "ev_demand_forecast_24h": [round(value, 6) for value in station.demand_forecast_24h],
                }
                for station in flow_inputs.stations
            ],
        }

    def _share_plan_24h(self, commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_hour: list[dict[str, Any]] = []
        for hour in range(HORIZON_HOURS):
            rows = [row for row in commands if row["hour"] == hour]
            by_hour.append(
                {
                    "hour": hour,
                    "share_plan": [
                        {"station_id": row["station_id"], "share_energy": row["share_energy_kwh"]}
                        for row in rows
                    ],
                    "total_share_energy": round(sum(row["share_energy_kwh"] for row in rows), 6),
                }
            )
        return by_hour

    def _summary(self, commands: list[dict[str, Any]]) -> dict[str, Any]:
        final_soc: dict[str, float] = {}
        for row in commands:
            final_soc[str(row["station_id"])] = row["soc_after"]
        return {
            "command_count": len(commands),
            "total_grid_kwh": round(sum(row["grid_total_kwh"] for row in commands), 6),
            "total_grid_cost": round(sum(row["grid_cost"] for row in commands), 6),
            "total_loss_kwh": round(sum(row["loss_kwh"] for row in commands), 6),
            "total_share_abs_kwh": round(sum(abs(row["share_energy_kwh"]) for row in commands), 6),
            "share_nonzero_rows": sum(1 for row in commands if abs(row["share_energy_kwh"]) > 1e-6),
            "total_peak_violation": round(sum(row["peak_violation"] for row in commands), 6),
            "total_soc_violation": round(sum(row["soc_violation"] for row in commands), 6),
            "safety_adjustment_count": sum(1 for row in commands if row.get("safety_adjusted")),
            "shield_active_rows": sum(1 for row in commands if row.get("shield_fired")),
            "shield_fired_counts": self._shield_fired_counts(commands),
            "final_soc_by_station": final_soc,
        }

    @staticmethod
    def _shield_fired_counts(commands: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in commands:
            for rule in row.get("shield_fired", []):
                counts[rule] = counts.get(rule, 0) + 1
        return counts

    @staticmethod
    def _scenario_validity(commands: list[dict[str, Any]], model_status: str | None = None) -> dict[str, Any]:
        """Explicit validity gate (Codex 2026-05-21 P1-4): a dispatch is only 'valid' when the
        shield kept every current peak breach feasible with no residual and no SoC breach. If the
        ESS is physically undersized for the case (e.g. depleted init_soc or demand beyond spec),
        report 'infeasible' with the residual rather than silently calling the run valid.

        The rule fallback path (no team model / model unavailable) emits zero-violation, shield-less
        commands, so it must NOT be reported as 'valid' — it was never physically evaluated.
        """
        # Only the genuine rule fallback (model unavailable / use_team_model=false) is unevaluated.
        # TEAM_FALLBACK_SHIELD_LOADED is the normal shield path and *is* physically evaluated.
        if model_status in ("FALLBACK_AFTER_TEAM_MODEL_UNAVAILABLE", "FALLBACK_REQUESTED"):
            return {
                "status": "unevaluated",
                "reason": (
                    "rule fallback path (model unavailable or use_team_model=false) does not run "
                    "the physical/shield validation; peak/SoC feasibility is not assessed."
                ),
                "model_status": model_status,
            }
        infeasible_rows = sum(
            1 for c in commands if c.get("shield_diag", {}).get("peak_relief_feasible", 1.0) == 0.0
        )
        max_residual = max(
            (c.get("shield_diag", {}).get("peak_residual_kwh", 0.0) for c in commands), default=0.0
        )
        total_peak_violation = sum(c.get("peak_violation", 0.0) for c in commands)
        total_soc_violation = sum(c.get("soc_violation", 0.0) for c in commands)
        is_valid = total_peak_violation <= 0.1 and total_soc_violation <= 1e-3 and infeasible_rows == 0
        return {
            "status": "valid" if is_valid else "infeasible",
            "peak_relief_infeasible_rows": infeasible_rows,
            "max_peak_residual_kwh": round(max_residual, 3),
            "total_peak_violation_kwh": round(total_peak_violation, 3),
            "total_soc_violation_kwh": round(total_soc_violation, 6),
            "min_init_soc_recommended": 0.3,
            "note": (
                "valid: shield feasible for the given init_soc and demand. infeasible: ESS is "
                "physically undersized for this case (raise starting SoC, reduce demand, or scale "
                "the hub spec). A depleted starting SoC cannot be fixed by overnight pre-charge "
                "within the horizon."
            ),
        }

    def _model_info_from_manifest(self, manifest: dict[str, Any], status: str) -> dict[str, Any]:
        evaluation_summary = self._read_evaluation_summary()
        return {
            "model_name": manifest.get("model_id"),
            "model_status": status,
            "upper_algo": manifest.get("algorithm", {}).get("upper_algo"),
            "lower_algo": manifest.get("algorithm", {}).get("lower_algo"),
            "train_data_mode": manifest.get("data", {}).get("train_data_mode"),
            "evaluation": evaluation_summary,
        }

    def _read_evaluation_summary(self) -> dict[str, Any] | None:
        path = TEAM_SAC_MODEL_PACKAGE_DIR / "evaluation_summary.csv"
        if not path.exists():
            return None
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) < 2:
            return None
        headers = lines[0].split(",")
        values = lines[1].split(",")
        return {key: self._maybe_number(value) for key, value in zip(headers, values, strict=False)}

    def _aggregate_ev_p50(self, payload: dict[str, Any]) -> tuple[list[float], str]:
        p50, _p90, source = self._aggregate_ev(payload)
        return p50, source

    def _aggregate_ev(self, payload: dict[str, Any]) -> tuple[list[float], list[float] | None, str]:
        """Returns (24h p50 aggregate, 24h p90 aggregate or None, source tag).

        The empirical p90 (from the EV service) is the realistic upper bound the shield must
        cover. Supplying it lets the dispatch use the true demand spread instead of the runtime's
        conservative p50*1.3 fallback. Explicit aggregate input has no p90 → None (fallback used).

        ev_scale is applied uniformly:
          - explicit aggregate_ev_demand_24h: multiplied here (Codex 2026-05-20 권고: path 통일)
          - upstream ev.predict: passed as scale parameter
        """
        scale = payload.get("ev_scale", 1.0)
        explicit = payload.get("aggregate_ev_demand_24h")
        if explicit is not None:
            raw = self._extract_24_values(explicit, ["ev_demand", "ev_demand_p50", "value"], [0.0] * HORIZON_HOURS)
            return [value * scale for value in raw], None, "request_aggregate_ev_demand_24h"

        response = self.ev.predict({"request_id": payload.get("request_id"), "scale": scale})
        if response["code"] != responses.SUCCESS:
            return [0.0] * HORIZON_HOURS, None, "ev_service_failed"
        rows = response["data"]["forecast_24h"]
        p50 = [float(row["ev_demand_p50"]) for row in rows]
        p90 = [float(row["ev_demand_p90"]) for row in rows] if rows and "ev_demand_p90" in rows[0] else None
        return p50, p90, "ev_service"

    def _top_level_pv_forecast(self, payload: dict[str, Any], capacity_kwh: float) -> PVForecastSelection:
        required = ["base_date", "encoder_weather_24h", "decoder_pv_24h"]
        if any(field not in payload for field in required):
            return PVForecastSelection(values=None, source="not_requested")
        response = self.pv.predict(
            {
                "request_id": payload.get("request_id"),
                "station_id": payload.get("station_id", "network_pv"),
                "base_date": payload["base_date"],
                "encoder_weather_24h": payload["encoder_weather_24h"],
                "encoder_weather_168h": payload.get("encoder_weather_168h"),
                "decoder_weather_24h": payload.get("decoder_weather_24h"),
                "future_weather_24h": payload.get("future_weather_24h"),
                "decoder_pv_24h": payload["decoder_pv_24h"],
                "pv_region": payload.get("pv_region") or payload.get("region") or payload.get("station_region"),
                "capacity_kwh": capacity_kwh,
            }
        )
        if response["code"] != responses.SUCCESS:
            return PVForecastSelection(
                values=None,
                source="pv_endpoint_failed",
                fallback_reason=response.get("message") or response.get("code"),
            )
        data = response["data"]
        model_status = data.get("model_status")
        if model_status == "TEAM_TFT_PV_LOADED":
            source = "han_tft_pv"
        elif model_status == "WEIGHTS_NOT_EXPORTED":
            source = "shadow_pv_predictor"
        else:
            source = "pv_endpoint"
        return PVForecastSelection(
            values=[float(row["pv_power"]) for row in data["predicted_pv_24h"]],
            source=source,
            model_name=data.get("model_name"),
            model_status=model_status,
            requested_region=data.get("requested_region"),
            loaded_region=data.get("loaded_region"),
            region_model_status=data.get("region_model_status"),
        )

    def _first_present(self, payload: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in payload:
                return payload[key]
        return None

    def _extract_24_values(self, value: Any, aliases: list[str], default: list[float]) -> list[float]:
        if value is None:
            return list(default)
        if not isinstance(value, list) or len(value) != HORIZON_HOURS:
            raise ValueError("24 hourly values are required")
        result = []
        for index, item in enumerate(value):
            if isinstance(item, dict):
                number = None
                for alias in aliases:
                    if alias in item:
                        number = as_number(item[alias])
                        break
            else:
                number = as_number(item)
            if number is None:
                raise ValueError(f"invalid hourly value at index {index}")
            result.append(float(number))
        return result

    def _optional_float_array(self, value: Any, label: str) -> list[float] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError(f"{label} must be an array")
        result = []
        for index, item in enumerate(value):
            number = as_number(item)
            if number is None:
                raise ValueError(f"invalid {label} value at index {index}")
            result.append(float(number))
        return result

    def _normalized_weights(self, value: Any, default: list[float]) -> list[float]:
        weights = self._optional_float_array(value, "station_demand_weights") if value is not None else list(default)
        if len(weights) != TEAM_STATION_COUNT or any(item < 0 for item in weights):
            raise ValueError("station_demand_weights must have 3 non-negative values")
        total = sum(weights)
        if total <= 0:
            raise ValueError("station_demand_weights total must be > 0")
        return [item / total for item in weights]

    def _normalized_pv_scales(self, value: Any, default: list[float]) -> list[float]:
        scales = self._optional_float_array(value, "station_pv_scales") if value is not None else list(default)
        if len(scales) != TEAM_STATION_COUNT or any(item < 0 for item in scales):
            raise ValueError("station_pv_scales must have 3 non-negative values")
        return scales

    def _number_or_default(self, value: Any, default: float) -> float:
        number = as_number(value)
        return default if number is None else float(number)

    def _maybe_number(self, value: str) -> str | float:
        number = as_number(value)
        return value if number is None else float(number)

    def _default_tou(self) -> list[float]:
        tou = [DEFAULT_TOU_LOW] * HORIZON_HOURS
        for hour in range(7, 12):
            tou[hour] = DEFAULT_TOU_MID
        for hour in range(12, 18):
            tou[hour] = DEFAULT_TOU_HIGH
        for hour in range(18, 21):
            tou[hour] = DEFAULT_TOU_MID
        return tou

    def _default_pv(self, capacity: float) -> list[float]:
        values = []
        for hour in range(HORIZON_HOURS):
            daylight = max(0.0, math.sin(math.pi * (hour - 6) / 12.0))
            values.append(round(capacity * daylight, 6))
        return values

    def _fallback_grid(self, pv: float, demand: float, share: float, a_ess: float, ess_capacity: float) -> float:
        received = max(0.0, share)
        exported = max(0.0, -share)
        internal_demand = max(0.0, demand - received) + exported
        ess_energy = a_ess * ess_capacity
        discharge = max(0.0, -ess_energy)
        charge = max(0.0, ess_energy)
        remaining_after_pv = max(0.0, internal_demand - pv - discharge)
        surplus_pv_after_demand = max(0.0, pv - internal_demand)
        grid_charge = max(0.0, charge - surplus_pv_after_demand)
        return remaining_after_pv + grid_charge

    def _safe_ess_action(self, a_ess: float, soc_before: float) -> float:
        lower = TEAM_SOC_MIN - soc_before
        upper = TEAM_SOC_MAX - soc_before
        return min(upper, max(lower, a_ess))

    def _command_label(self, a_ess: float, a_pv: float) -> str:
        if a_ess > 1e-6:
            ess = "charge_ess"
        elif a_ess < -1e-6:
            ess = "discharge_ess"
        else:
            ess = "hold_ess"
        pv = "pv_to_ev_first" if a_pv >= 0.5 else "pv_to_ess_first"
        return f"{ess}:{pv}"
