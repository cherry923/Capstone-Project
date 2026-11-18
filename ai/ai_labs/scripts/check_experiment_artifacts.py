#!/usr/bin/env python3
"""Check the offline experiment artifacts used by the AI lab docs.

Run from the project root:

    python3 ai/ai_labs/scripts/check_experiment_artifacts.py

The script is intentionally dependency-free so teammates can run it without the
ai_module virtualenv.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]


REQUIRED_ARTIFACTS = {
    "frontend_comparison_json": PROJECT_ROOT
    / "server/frontend/public/assets/operation-comparison/evonly_vmoderate_v2p90_pvess_multiseed.json",
    "final_decision_result_json": PROJECT_ROOT
    / "ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42_physical_oracle.json",
    "final_corrected_tariff_json": PROJECT_ROOT
    / "ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42.json",
    "pv_tree_evtfm_v2_p90_meta": PROJECT_ROOT
    / "ai_module/artifacts/sharing_3arm/forecast_observation/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90.json",
    "evtfm_v2_p90_meta": PROJECT_ROOT
    / "ai_module/artifacts/sharing_3arm/forecast_observation/multi_pv6000_shift048_evtfm_v2_peakaware_shapecal_p90.json",
    "main_train_csv": PROJECT_ROOT
    / "data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_train.csv",
    "main_test_csv": PROJECT_ROOT
    / "data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_test.csv",
}


OPTIONAL_ARTIFACTS = {
    "current_status_md": PROJECT_ROOT / "ai_module/artifacts/report_assets/current_completed_ai_status_2026-05-28.md",
    "algorithm_explanation_md": PROJECT_ROOT
    / "ai_module/artifacts/report_assets/ai_model_algorithm_explanation_2026-05-28.md",
    "representative_week_png": PROJECT_ROOT
    / "ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_actual_timeseries_representative_week_2022.png",
    "wape_by_station_png": PROJECT_ROOT
    / "ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_wape_by_station_jan_feb_2022.png",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def pct(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):+.2f}%"


def mkrw(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value) / 1_000_000:.3f}"


def check_paths(strict: bool) -> bool:
    ok = True
    print("# Artifact Presence")
    for group_name, artifacts in (("required", REQUIRED_ARTIFACTS), ("optional", OPTIONAL_ARTIFACTS)):
        print(f"\n## {group_name}")
        for key, path in artifacts.items():
            exists = path.exists()
            mark = "OK" if exists else "MISSING"
            print(f"- {mark:7} {key}: {rel(path)}")
            if group_name == "required" and not exists:
                ok = False
    if strict and not ok:
        print("\nRequired artifacts are missing.")
    return ok


def print_forecast_summary() -> None:
    path = REQUIRED_ARTIFACTS["frontend_comparison_json"]
    if not path.exists():
        return
    data = load_json(path)
    metrics = data.get("forecastMetrics", [])
    if not metrics:
        return
    print("\n# Forecast Metrics (frontend/report source)")
    print("| metric | value | note |")
    print("|---|---:|---|")
    for row in metrics:
        print(f"| {row.get('label', '-')} | {row.get('value', '-')} {row.get('unit', '')} | {row.get('note', '-')} |")


def print_decision_summary() -> None:
    path = REQUIRED_ARTIFACTS["final_decision_result_json"]
    if not path.exists():
        return
    data = load_json(path)
    meta = data.get("meta", {})
    methods = data.get("methods", {})

    print("\n# Decision Result")
    if meta:
        print(f"- Date range: {meta.get('start_date', '-')} to {meta.get('end_date', '-')}")
        print(f"- Demand charge rate: {meta.get('demand_charge_rate', '-')} KRW/kW-month")
        print(f"- Test CSV: {meta.get('test_csv', '-')}")
        print(f"- Aggregate seeds: {', '.join(meta.get('aggregated_seed_keys', []))}")

    print("\n| method | total@8320 M KRW | net M KRW | vs grid-only | vs passive-PV | vs local no-P2P | peak_v | share/day |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for key in (
        "grid_only_no_pv",
        "default_no_control",
        "no_sharing_sac",
        "shared_multi_sac",
        "milp_milp_oracle_total_tariff",
    ):
        row = methods.get(key, {})
        if not row:
            continue
        print(
            f"| {key} "
            f"| {mkrw(row.get('total_with_demand_charge_8320'))} "
            f"| {mkrw(row.get('net'))} "
            f"| {pct(row.get('total8320_vs_grid_only_pct'))} "
            f"| {pct(row.get('total8320_vs_passive_pv_pct'))} "
            f"| {pct(row.get('total8320_vs_no_sharing_sac_pct'))} "
            f"| {float(row.get('peak_v', 0)):.1f} "
            f"| {float(row.get('share_per_day', 0)):.0f} |"
        )


def print_pv_model_summary() -> None:
    path = REQUIRED_ARTIFACTS["pv_tree_evtfm_v2_p90_meta"]
    if not path.exists():
        return
    data = load_json(path)
    print("\n# PV/EV Scenario Metadata")
    print(f"- Selected PV model: {data.get('selected_pv_model', '-')}")
    inputs = data.get("inputs", {})
    for key in ("ev_forecast_train_csv", "ev_forecast_test_csv"):
        if key in inputs:
            print(f"- {key}: {inputs[key]}")
    outputs = data.get("outputs", {})
    for key in ("train_csv", "test_csv"):
        if key in outputs:
            print(f"- {key}: {outputs[key]}")
    scores = data.get("jan_feb_scores", [])
    if scores:
        score = scores[0]
        print(
            "- Jan-Feb PV score: "
            f"hourly WAPE {score.get('hourly_wape', 0):.2f}%, "
            f"daily WAPE {score.get('daily_total_wape', 0):.2f}%, "
            f"bias {score.get('bias_pct', 0):+.2f}%"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="exit non-zero when required artifacts are missing")
    args = parser.parse_args()

    ok = check_paths(strict=args.strict)
    print_forecast_summary()
    print_decision_summary()
    print_pv_model_summary()

    return 0 if ok or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
