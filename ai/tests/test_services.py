from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from app import responses
from app.services.decision import LowerDecisionService, MultiStationDecisionService, UpperDecisionService
from app.services.ev_forecast import EVDemandForecastService
from app.services.flow import DispatchFlowService
from app.services.pv_prediction import PVPredictionService


AI_REPO_ROOT = Path(__file__).resolve().parents[1]
CAPSTONE_ROOT = AI_REPO_ROOT.parent
FINAL_FORECAST_CONTRACT = AI_REPO_ROOT / "ai_labs/data/final_forecast_contract.json"
FINAL_PV_EV_META = (
    CAPSTONE_ROOT
    / "ai_module/artifacts/sharing_3arm/forecast_observation/"
    "multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90.json"
)
FINAL_EV_META = (
    CAPSTONE_ROOT
    / "ai_module/artifacts/sharing_3arm/forecast_observation/"
    "multi_pv6000_shift048_evtfm_v2_peakaware_shapecal_p90.json"
)
FINAL_SCENARIO_CSV = (
    CAPSTONE_ROOT
    / "data/processed/ev/sharing_3arm/"
    "multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_test.csv"
)
FRONTEND_COMPARISON_JSON = (
    CAPSTONE_ROOT
    / "server/frontend/public/assets/operation-comparison/evonly_vmoderate_v2p90_pvess_multiseed.json"
)
FINAL_PERIOD_START = "2022-01-01"
FINAL_PERIOD_END = "2022-02-28"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def final_period_rows() -> list[dict[str, str]]:
    with FINAL_SCENARIO_CSV.open("r", encoding="utf-8", newline="") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if FINAL_PERIOD_START <= row["date"] <= FINAL_PERIOD_END
        ]


def wape(actual: list[float], predicted: list[float]) -> float:
    denominator = max(sum(abs(value) for value in actual), 1e-9)
    return sum(abs(a - p) for a, p in zip(actual, predicted, strict=True)) / denominator * 100.0


def weather_24h() -> list[dict[str, float]]:
    rows = []
    for hour in range(24):
        rows.append(
            {
                "hour": hour,
                "temperature": 22.0,
                "rain": 0.0,
                "humidity": 55.0,
                "snow": 0.0,
                "cloud": 3.0,
                "duration": 1.0 if 7 <= hour <= 18 else 0.0,
                "radiation": 2.8 if 8 <= hour <= 17 else 0.0,
                "day": 0.0,
            }
        )
    return rows


def pv_24h() -> list[dict[str, float]]:
    return [{"hour": hour, "pv_power": 100.0 if 8 <= hour <= 17 else 0.0} for hour in range(24)]


def station_payload() -> dict:
    return {
        "request_id": "req-decision-test",
        "timezone": "Asia/Seoul",
        "time": 14,
        "stations": [
            {"station_id": 1, "ess_soc": 0.82, "pv_power": 9.0, "ev_demand": 3.0, "tou_price": 100},
            {"station_id": 2, "ess_soc": 0.44, "pv_power": 1.0, "ev_demand": 7.0, "tou_price": 100},
            {"station_id": 3, "ess_soc": 0.65, "pv_power": 4.0, "ev_demand": 4.0, "tou_price": 100},
        ],
    }


class FinalForecastArtifactTests(unittest.TestCase):
    """Frontend/report source-of-truth forecast contracts.

    The live PV endpoint can still load Han's TFT-style runtime package. The
    final report/frontend comparison, however, is backed by offline artifacts:
    PV tree regression + EV Transformer v2 p90.
    """

    def test_final_pv_forecast_uses_tree_regression_model(self) -> None:
        contract = load_json(FINAL_FORECAST_CONTRACT)
        data = load_json(FINAL_PV_EV_META) if FINAL_PV_EV_META.exists() else None

        self.assertEqual(contract["pv"]["model"], "tree_v5_hgb_absolute_error")
        self.assertEqual(contract["pv"]["model_family"], "tree_based_regression")
        self.assertEqual(contract["pv"]["implementation"], "HistGradientBoostingRegressor")
        self.assertIn("Strict day-ahead PV target", contract["pv"]["forecast_policy"])
        self.assertIn("hour_sin", contract["pv"]["features_include"])
        self.assertIn("ilsa", contract["pv"]["features_include"])
        self.assertIn("cf_lag24", contract["pv"]["features_include"])
        self.assertIn("cf_roll168", contract["pv"]["features_include"])

        jan_feb = contract["pv"]["jan_feb_2022"]
        self.assertAlmostEqual(jan_feb["hourly_wape"], 12.007659258578366, places=6)
        self.assertAlmostEqual(jan_feb["daily_total_wape"], 4.982481926316072, places=6)

        if data is not None:
            self.assertEqual(data["schema_version"], "sharing-pv-tree-ev-forecast-observation-v5")
            self.assertEqual(data["selected_pv_model"], contract["pv"]["model"])
            self.assertEqual(data["config"]["forecast_policy"], contract["pv"]["forecast_policy"])
            self.assertEqual(data["jan_feb_scores"][0]["scored_rows"], jan_feb["scored_rows"])

    def test_final_ev_forecast_uses_transformer_v2_p90_artifact(self) -> None:
        contract = load_json(FINAL_FORECAST_CONTRACT)
        data = load_json(FINAL_EV_META) if FINAL_EV_META.exists() else None

        self.assertEqual(contract["ev"]["model"], "evtfm_v2_peakaware_shapecal_p90")
        self.assertEqual(contract["ev"]["model_family"], "EV Transformer v2")
        self.assertIn("target-day actual demand is not an input", contract["ev"]["forecast_policy"])

        jan_feb = contract["ev"]["jan_feb_2022"]
        self.assertAlmostEqual(jan_feb["hourly_wape_p50"], 8.801471670039636, places=6)
        self.assertAlmostEqual(jan_feb["peak_hour_wape"], 5.42, places=2)
        self.assertGreater(jan_feb["coverage_actual_le_p90_pct"], 75.0)
        self.assertLessEqual(jan_feb["max_p90"], 800.0)

        if data is not None:
            self.assertEqual(data["schema_version"], "sharing-ev-demand-p90-v1")
            self.assertEqual(data["config"]["quantile"], 0.9)
            self.assertEqual(data["metrics"]["jan_feb_2022"]["days"], 59)
            self.assertAlmostEqual(
                data["metrics"]["jan_feb_2022"]["hourly_wape_p50"],
                jan_feb["hourly_wape_p50"],
                places=6,
            )

    def test_final_frontend_metrics_match_current_report_values(self) -> None:
        contract = load_json(FINAL_FORECAST_CONTRACT)
        data = load_json(FRONTEND_COMPARISON_JSON) if FRONTEND_COMPARISON_JSON.exists() else None

        self.assertEqual(contract["period"]["start"], FINAL_PERIOD_START)
        self.assertEqual(contract["period"]["end"], FINAL_PERIOD_END)

        metrics = {item["label"]: item["value"] for item in contract["frontend_metrics"]}
        self.assertAlmostEqual(metrics["PV 시간별 오차율"], 12.01, places=2)
        self.assertAlmostEqual(metrics["PV 일별 발전량 오차율"], 4.98, places=2)
        self.assertAlmostEqual(metrics["EV 시간별 오차율"], 8.80, places=2)
        self.assertAlmostEqual(metrics["EV 피크 수요 오차율"], 5.42, places=2)

        if data is not None:
            self.assertEqual(data["meta"]["primarySavingsBaseline"], "passive_pv_default")
            self.assertEqual(data["meta"]["sourceCsv"], contract["source_paths"]["scenario_csv"])
            self.assertEqual(data["meta"]["period"]["start"], FINAL_PERIOD_START)
            self.assertEqual(data["meta"]["period"]["end"], FINAL_PERIOD_END)
            self.assertEqual(
                data["meta"]["resultAggregation"],
                "Decision cost/saving metrics are 3-seed mean for seeds 1, 2, and 42.",
            )

    def test_final_scenario_contract_has_24h_station_pv_ev_forecasts(self) -> None:
        contract = load_json(FINAL_FORECAST_CONTRACT)
        summary = contract["scenario_csv_summary"]

        self.assertEqual(summary["rows"], 59 * 3 * 24)
        self.assertEqual(summary["stations"], ["0", "1", "2"])
        self.assertEqual(summary["hours"], 24)
        self.assertTrue(summary["demand_p90_is_at_least_forecast"])
        self.assertAlmostEqual(summary["pv_hourly_wape_recomputed"], 12.007659258578366, places=6)

        if not FINAL_SCENARIO_CSV.exists():
            return

        rows = final_period_rows()
        self.assertEqual(len(rows), summary["rows"])
        self.assertEqual(len({row["date"] for row in rows}), contract["period"]["days"])
        self.assertEqual(sorted({row["station"] for row in rows}), summary["stations"])
        self.assertEqual(sorted({int(row["hour"]) for row in rows}), list(range(summary["hours"])))
        for row in rows:
            self.assertGreaterEqual(float(row["pv_forecast"]), 0.0)
            self.assertGreaterEqual(float(row["demand_forecast"]), 0.0)
            self.assertGreaterEqual(float(row["demand_p90"]), 0.0)
            self.assertGreaterEqual(float(row["pv_actual"]), 0.0)
            self.assertGreaterEqual(float(row["demand_actual"]), 0.0)
            self.assertGreaterEqual(float(row["demand_p90"]), float(row["demand_forecast"]) - 1e-9)

        pv_actual = [float(row["pv_actual"]) for row in rows]
        pv_forecast = [float(row["pv_forecast"]) for row in rows]
        self.assertAlmostEqual(wape(pv_actual, pv_forecast), summary["pv_hourly_wape_recomputed"], places=6)


class RuntimePredictionServiceTests(unittest.TestCase):
    def test_runtime_pv_prediction_endpoint_contract(self) -> None:
        service = PVPredictionService()
        result = service.predict(
            {
                "request_id": "req-pv",
                "station_id": 1,
                "base_date": "2026-04-14",
                "capacity_kwh": 50.0,
                "encoder_weather_24h": weather_24h(),
                "decoder_pv_24h": pv_24h(),
            }
        )
        self.assertEqual(result["code"], responses.SUCCESS)
        self.assertEqual(result["data"]["target_date"], "2026-04-15")
        self.assertEqual(len(result["data"]["predicted_pv_24h"]), 24)
        self.assertTrue(all(row["pv_power"] >= 0 for row in result["data"]["predicted_pv_24h"]))
        self.assertTrue(all(row["pv_power"] <= 50.0 for row in result["data"]["predicted_pv_24h"]))
        self.assertEqual(result["data"]["output_unit"], "kWh")
        self.assertEqual(result["data"]["output_scaling"]["requested_capacity_kwh"], 50.0)

    def test_runtime_ev_forecast_endpoint_loads_configured_payload(self) -> None:
        service = EVDemandForecastService()
        result = service.predict({"request_id": "req-ev", "station_id": 1})
        self.assertEqual(result["code"], responses.SUCCESS)
        self.assertEqual(len(result["data"]["forecast_24h"]), 24)
        self.assertIn("model_name", result["data"])


class DecisionServiceTests(unittest.TestCase):
    def test_share_plan_conserves_energy(self) -> None:
        result = UpperDecisionService().generate_share_plan(station_payload())
        self.assertEqual(result["code"], responses.SUCCESS)
        share_plan = result["data"]["share_plan"]
        self.assertEqual(len(share_plan), 3)
        self.assertAlmostEqual(sum(row["share_energy"] for row in share_plan), 0.0, places=5)

    def test_local_policy_returns_sac_action_shape(self) -> None:
        result = LowerDecisionService().generate_local_policy(
            {
                "request_id": "req-local",
                "station_id": 1,
                "time": 14,
                "ess_soc": 0.7,
                "pv_power": 3.5,
                "ev_demand": 5.0,
                "tou_price": 100,
                "share_energy": 1.2,
            }
        )
        self.assertEqual(result["code"], responses.SUCCESS)
        self.assertIn("a_ess", result["data"])
        self.assertIn("a_pv", result["data"])
        self.assertGreaterEqual(result["data"]["a_pv"], 0.0)
        self.assertLessEqual(result["data"]["a_pv"], 1.0)

    def test_multi_station_chains_upper_and_lower(self) -> None:
        result = MultiStationDecisionService().generate(station_payload())
        self.assertEqual(result["code"], responses.SUCCESS)
        self.assertEqual(len(result["data"]["share_plan"]["share_plan"]), 3)
        self.assertEqual(len(result["data"]["local_policies"]), 3)

    def test_dispatch_flow_returns_24h_station_commands(self) -> None:
        result = DispatchFlowService().generate_dispatch_24h(
            {
                "request_id": "req-flow",
                "target_date": "2026-05-07",
                "use_team_model": False,
                "init_soc": [0.55, 0.5, 0.45],
            }
        )
        self.assertEqual(result["code"], responses.SUCCESS)
        data = result["data"]
        self.assertEqual(data["station_count"], 3)
        self.assertEqual(len(data["dispatch"]["commands"]), 72)
        self.assertEqual(data["dispatch"]["summary"]["command_count"], 72)
        self.assertEqual(data["forecasts"]["source"]["pv"], "daylight_fallback")
        self.assertTrue(
            all(row["source"] == "daylight_fallback" for row in data["forecasts"]["source"]["pv_detail"]["station_sources"])
        )
        self.assertTrue(
            all(abs(row["total_share_energy"]) < 1e-4 for row in data["dispatch"]["share_plan_24h"])
        )

    def test_dispatch_flow_reports_station_pv_payload_source(self) -> None:
        stations = [
            {"station_id": 1, "pv_forecast_24h": [0.0] * 24},
            {"station_id": 2, "predicted_pv_24h": [{"hour": hour, "pv_power": 2.0} for hour in range(24)]},
            {"station_id": 3, "pv_forecast_24h": [{"hour": hour, "value": 3.0} for hour in range(24)]},
        ]
        result = DispatchFlowService().generate_dispatch_24h(
            {
                "request_id": "req-flow-station-pv",
                "target_date": "2026-05-07",
                "use_team_model": False,
                "stations": stations,
            }
        )

        self.assertEqual(result["code"], responses.SUCCESS)
        source = result["data"]["forecasts"]["source"]
        self.assertEqual(source["pv"], "station_payload")
        self.assertEqual(
            [row["source"] for row in source["pv_detail"]["station_sources"]],
            ["station_payload", "station_payload", "station_payload"],
        )

    def test_dispatch_flow_reports_han_pv_top_level_source(self) -> None:
        service = DispatchFlowService()

        def fake_predict(payload: dict) -> dict:
            return responses.ok(
                payload.get("request_id"),
                {
                    "station_id": payload["station_id"],
                    "base_date": payload["base_date"],
                    "target_date": "2026-05-08",
                    "predicted_pv_24h": [{"hour": hour, "pv_power": 10.0} for hour in range(24)],
                    "model_name": "fake-han-tft",
                    "model_status": "TEAM_TFT_PV_LOADED",
                    "requested_region": payload.get("pv_region"),
                    "loaded_region": "인천시",
                    "region_model_status": "FALLBACK_TO_LOADED_REGION_MODEL",
                },
            )

        service.pv.predict = fake_predict
        result = service.generate_dispatch_24h(
            {
                "request_id": "req-flow-han-pv",
                "target_date": "2026-05-07",
                "base_date": "2026-05-06",
                "use_team_model": False,
                "encoder_weather_24h": weather_24h(),
                "decoder_pv_24h": pv_24h(),
                "pv_region": "서울시",
            }
        )

        self.assertEqual(result["code"], responses.SUCCESS)
        source = result["data"]["forecasts"]["source"]
        self.assertEqual(source["pv"], "han_tft_pv")
        self.assertEqual(source["pv_detail"]["network_model_name"], "fake-han-tft")
        self.assertEqual(source["pv_detail"]["network_model_status"], "TEAM_TFT_PV_LOADED")
        self.assertEqual(source["pv_detail"]["requested_region"], "서울시")
        self.assertEqual(source["pv_detail"]["loaded_region"], "인천시")
        self.assertEqual(source["pv_detail"]["region_model_status"], "FALLBACK_TO_LOADED_REGION_MODEL")

    def test_dispatch_flow_emits_historical_scenario_warning(self) -> None:
        result = DispatchFlowService().generate_dispatch_24h(
            {
                "request_id": "req-historical-warning",
                "target_date": "2026-05-07",
                "use_team_model": False,
                "init_soc": [0.55, 0.5, 0.45],
            }
        )
        self.assertEqual(result["code"], responses.SUCCESS)
        data = result["data"]
        ev_detail = data["forecasts"]["source"]["ev_detail"]
        self.assertTrue(ev_detail["historical_scenario"])
        self.assertEqual(ev_detail["mode"], "historical_fixed_payload")
        self.assertTrue(ev_detail["payload_available"])
        self.assertIsInstance(ev_detail["target_date_mismatch_days"], int)
        self.assertGreater(ev_detail["target_date_mismatch_days"], 365)
        warnings = data["warnings"]
        self.assertTrue(any("historical payload" in msg for msg in warnings))

    def test_dispatch_flow_strict_target_date_rejects(self) -> None:
        import os

        os.environ["EV_STRICT_TARGET_DATE"] = "1"
        os.environ["EV_STRICT_MISMATCH_DAYS"] = "365"
        try:
            import importlib
            from app import settings as settings_module
            from app.services import flow as flow_module

            importlib.reload(settings_module)
            importlib.reload(flow_module)

            result = flow_module.DispatchFlowService().generate_dispatch_24h(
                {
                    "request_id": "req-strict-reject",
                    "target_date": "2026-05-07",
                    "use_team_model": False,
                }
            )
            self.assertEqual(result["code"], responses.INVALID_INPUT_VALUE)
            self.assertIn("EV_STRICT_MISMATCH_DAYS", result["message"])
        finally:
            os.environ.pop("EV_STRICT_TARGET_DATE", None)
            os.environ.pop("EV_STRICT_MISMATCH_DAYS", None)
            import importlib
            from app import settings as settings_module
            from app.services import flow as flow_module

            importlib.reload(settings_module)
            importlib.reload(flow_module)


if __name__ == "__main__":
    unittest.main()
