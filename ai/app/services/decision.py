from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app import responses
from app.settings import (
    DEFAULT_ESS_CAPACITY_KWH,
    DEFAULT_ESS_POWER_LIMIT_KWH,
    DEFAULT_SHARE_LIMIT_KWH,
    SOC_MIN,
    SOC_RESERVE,
    SOC_TARGET,
)
from app.validation import as_number, missing, require_number


@dataclass
class Station:
    station_id: int | str
    ess_soc: float
    pv_power: float
    ev_demand: float
    tou_price: float
    ess_capacity_kwh: float = DEFAULT_ESS_CAPACITY_KWH
    ess_power_limit_kwh: float = DEFAULT_ESS_POWER_LIMIT_KWH
    max_import_kwh: float = DEFAULT_SHARE_LIMIT_KWH
    max_export_kwh: float = DEFAULT_SHARE_LIMIT_KWH


class UpperDecisionService:
    """Upper multi-station sharing policy.

    This mirrors the team SAC/MILP tester constraint that share_energy sums to
    zero, while keeping a deterministic rule path for API and backend testing.
    """

    def generate_share_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("request_id")
        validation_error = self._validate_payload(payload)
        if validation_error:
            return responses.error(request_id, validation_error[0], validation_error[1])

        stations = [self._parse_station(row) for row in payload["stations"]]
        share_by_id, transfers = self._build_share_plan(stations)

        share_plan = [
            {"station_id": station.station_id, "share_energy": round(share_by_id[station.station_id], 6)}
            for station in stations
        ]
        total_share = round(sum(row["share_energy"] for row in share_plan), 6)
        if abs(total_share) > 1e-4:
            return responses.error(request_id, responses.POST_PROCESSING_FAILED, "share_energy conservation failed")

        return responses.ok(
            request_id,
            {
                "time": int(payload["time"]),
                "share_plan": share_plan,
                "transfers": transfers,
                "model_name": "upper_milp_lite_shadow",
                "model_status": "RULE_BASED_UNTIL_RL_WEIGHTS_EXPORTED",
                "total_share_energy": total_share,
            },
        )

    def _validate_payload(self, payload: dict[str, Any]) -> tuple[str, str] | None:
        missing_field = missing(payload, ["time", "stations"])
        if missing_field:
            return responses.MISSING_REQUIRED_FIELD, f"missing field: {missing_field}"
        time = as_number(payload["time"])
        if time is None or int(time) != time or not 0 <= int(time) <= 23:
            return responses.INVALID_INPUT_VALUE, "time must be an integer from 0 to 23"
        if not isinstance(payload["stations"], list):
            return responses.INVALID_ARRAY_LENGTH, "stations must be an array"
        if len(payload["stations"]) == 0:
            return responses.INVALID_ARRAY_LENGTH, "stations must not be empty"
        for index, row in enumerate(payload["stations"]):
            if not isinstance(row, dict):
                return responses.INSUFFICIENT_INPUT_DATA, f"station[{index}] must be an object"
            missing_station_field = missing(row, ["station_id", "ess_soc", "pv_power", "ev_demand", "tou_price"])
            if missing_station_field:
                return responses.INSUFFICIENT_INPUT_DATA, f"station[{index}] missing {missing_station_field}"
            parsed = self._parse_station(row)
            if not 0 <= parsed.ess_soc <= 1:
                return responses.INVALID_INPUT_VALUE, "ess_soc must be between 0 and 1"
            if parsed.pv_power < 0 or parsed.ev_demand < 0 or parsed.tou_price < 0:
                return responses.INVALID_INPUT_VALUE, "pv_power, ev_demand, tou_price must be >= 0"
        return None

    def _parse_station(self, row: dict[str, Any]) -> Station:
        return Station(
            station_id=row["station_id"],
            ess_soc=float(row["ess_soc"]),
            pv_power=float(row["pv_power"]),
            ev_demand=float(row["ev_demand"]),
            tou_price=float(row["tou_price"]),
            ess_capacity_kwh=float(row.get("ess_capacity_kwh", DEFAULT_ESS_CAPACITY_KWH)),
            ess_power_limit_kwh=float(row.get("ess_power_limit_kwh", DEFAULT_ESS_POWER_LIMIT_KWH)),
            max_import_kwh=float(row.get("max_import_kwh", DEFAULT_SHARE_LIMIT_KWH)),
            max_export_kwh=float(row.get("max_export_kwh", DEFAULT_SHARE_LIMIT_KWH)),
        )

    def _build_share_plan(self, stations: list[Station]) -> tuple[dict[int | str, float], list[dict[str, Any]]]:
        share_by_id: dict[int | str, float] = {station.station_id: 0.0 for station in stations}
        exporters = []
        importers = []

        for station in stations:
            net_pv = station.pv_power - station.ev_demand
            reserve_energy = max(0.0, station.ess_soc - SOC_RESERVE) * station.ess_capacity_kwh
            export_limit = min(station.max_export_kwh, station.ess_power_limit_kwh, reserve_energy)
            import_limit = station.max_import_kwh

            exportable = min(max(0.0, net_pv) + export_limit, station.max_export_kwh)
            needed = min(max(0.0, -net_pv), import_limit)

            if exportable > 1e-9:
                exporters.append({"station": station, "remaining": exportable})
            if needed > 1e-9:
                importers.append({"station": station, "remaining": needed})

        exporters.sort(key=lambda item: (-item["remaining"], -item["station"].ess_soc))
        importers.sort(key=lambda item: (-item["remaining"], item["station"].ess_soc))

        transfers: list[dict[str, Any]] = []
        for importer in importers:
            for exporter in exporters:
                if importer["remaining"] <= 1e-9:
                    break
                if exporter["remaining"] <= 1e-9:
                    continue
                amount = min(importer["remaining"], exporter["remaining"])
                importer["remaining"] -= amount
                exporter["remaining"] -= amount
                from_id = exporter["station"].station_id
                to_id = importer["station"].station_id
                share_by_id[from_id] -= amount
                share_by_id[to_id] += amount
                transfers.append(
                    {
                        "from_station_id": from_id,
                        "to_station_id": to_id,
                        "energy_kwh": round(amount, 6),
                        "loss_kwh": 0.0,
                    }
                )

        return share_by_id, transfers


class LowerDecisionService:
    """Lower station policy for ESS/PV control.

    SAC weights can later replace _select_action. Until then, this preserves the
    paper action semantics: a_ess controls ESS charge/discharge and a_pv controls
    PV allocation priority.
    """

    def generate_local_policy(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("request_id")
        validation_error = self._validate_payload(payload)
        if validation_error:
            return responses.error(request_id, validation_error[0], validation_error[1])

        try:
            action = self._select_action(payload)
            policy = self._postprocess(action, payload)
        except Exception:
            policy = {"a_ess": 0.0, "a_pv": 1.0, "fallback": True}

        return responses.ok(
            request_id,
            {
                "station_id": payload["station_id"],
                "time": int(payload["time"]),
                "a_ess": policy["a_ess"],
                "a_pv": policy["a_pv"],
                "fallback": policy.get("fallback", False),
                "model_name": "lower_sac_shadow_policy",
                "model_status": "RULE_BASED_UNTIL_SAC_WEIGHTS_EXPORTED",
            },
        )

    def _validate_payload(self, payload: dict[str, Any]) -> tuple[str, str] | None:
        required = ["station_id", "time", "ess_soc", "pv_power", "ev_demand", "tou_price", "share_energy"]
        missing_field = missing(payload, required)
        if missing_field:
            return responses.MISSING_REQUIRED_FIELD, f"missing field: {missing_field}"

        time = as_number(payload["time"])
        if time is None or int(time) != time or not 0 <= int(time) <= 23:
            return responses.INVALID_INPUT_VALUE, "time must be an integer from 0 to 23"

        for field in ["ess_soc", "pv_power", "ev_demand", "tou_price", "share_energy"]:
            _, error_code = require_number(payload, field)
            if error_code:
                return error_code, f"invalid numeric field: {field}"

        ess_soc = float(payload["ess_soc"])
        if not 0 <= ess_soc <= 1:
            return responses.INVALID_INPUT_VALUE, "ess_soc must be between 0 and 1"
        if float(payload["pv_power"]) < 0 or float(payload["ev_demand"]) < 0 or float(payload["tou_price"]) < 0:
            return responses.INVALID_INPUT_VALUE, "pv_power, ev_demand, tou_price must be >= 0"
        return None

    def _select_action(self, payload: dict[str, Any]) -> dict[str, float]:
        ess_soc = float(payload["ess_soc"])
        pv_power = float(payload["pv_power"])
        ev_demand = float(payload["ev_demand"])
        share_energy = float(payload["share_energy"])
        ess_capacity = float(payload.get("ess_capacity_kwh", DEFAULT_ESS_CAPACITY_KWH))
        ess_power_limit = float(payload.get("ess_power_limit_kwh", DEFAULT_ESS_POWER_LIMIT_KWH))
        max_soc_delta = ess_power_limit / ess_capacity

        net = pv_power + share_energy - ev_demand
        if net > 0 and ess_soc < SOC_TARGET:
            a_ess = min(max_soc_delta, net / ess_capacity, SOC_TARGET - ess_soc)
        elif net < 0 and ess_soc > SOC_RESERVE:
            a_ess = -min(max_soc_delta, abs(net) / ess_capacity, ess_soc - SOC_RESERVE)
        else:
            a_ess = 0.0

        if pv_power <= 1e-9:
            a_pv = 1.0
        elif ev_demand >= pv_power:
            a_pv = 1.0
        elif ess_soc < SOC_TARGET:
            a_pv = max(0.0, min(1.0, ev_demand / pv_power))
        else:
            a_pv = 1.0

        return {"a_ess": a_ess, "a_pv": a_pv}

    def _postprocess(self, action: dict[str, float], payload: dict[str, Any]) -> dict[str, float]:
        ess_capacity = float(payload.get("ess_capacity_kwh", DEFAULT_ESS_CAPACITY_KWH))
        ess_power_limit = float(payload.get("ess_power_limit_kwh", DEFAULT_ESS_POWER_LIMIT_KWH))
        max_soc_delta = ess_power_limit / ess_capacity
        ess_soc = float(payload["ess_soc"])

        lower = max(-max_soc_delta, SOC_MIN - ess_soc)
        upper = min(max_soc_delta, 1.0 - ess_soc)
        a_ess = min(upper, max(lower, float(action["a_ess"])))
        a_pv = min(1.0, max(0.0, float(action["a_pv"])))
        return {"a_ess": round(a_ess, 6), "a_pv": round(a_pv, 6)}


class MultiStationDecisionService:
    def __init__(self) -> None:
        self.upper = UpperDecisionService()
        self.lower = LowerDecisionService()

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("request_id")
        share_response = self.upper.generate_share_plan(payload)
        if share_response["code"] != responses.SUCCESS:
            zero_plan = [
                {"station_id": station.get("station_id"), "share_energy": 0.0}
                for station in payload.get("stations", [])
                if isinstance(station, dict)
            ]
            share_data = {
                "time": payload.get("time"),
                "share_plan": zero_plan,
                "transfers": [],
                "model_name": "upper_fallback_zero_share",
                "model_status": "FALLBACK_AFTER_UPPER_FAILURE",
                "total_share_energy": 0.0,
            }
        else:
            share_data = share_response["data"]

        share_by_id = {
            row["station_id"]: row["share_energy"] for row in share_data.get("share_plan", [])
        }
        local_policies = []
        for station in payload.get("stations", []):
            local_payload = {
                "request_id": request_id,
                "timezone": payload.get("timezone"),
                "station_id": station.get("station_id"),
                "time": payload.get("time"),
                "ess_soc": station.get("ess_soc"),
                "pv_power": station.get("pv_power"),
                "ev_demand": station.get("ev_demand"),
                "tou_price": station.get("tou_price"),
                "share_energy": share_by_id.get(station.get("station_id"), 0.0),
                "ess_capacity_kwh": station.get("ess_capacity_kwh", DEFAULT_ESS_CAPACITY_KWH),
                "ess_power_limit_kwh": station.get("ess_power_limit_kwh", DEFAULT_ESS_POWER_LIMIT_KWH),
            }
            local_response = self.lower.generate_local_policy(local_payload)
            local_policies.append(local_response)

        return responses.ok(
            request_id,
            {
                "time": payload.get("time"),
                "share_plan": share_data,
                "local_policies": [item["data"] if item["code"] == responses.SUCCESS else item for item in local_policies],
            },
        )

