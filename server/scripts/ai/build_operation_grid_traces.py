#!/usr/bin/env python3
"""Build exact operation-detail grid traces from saved experiment artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pulp
from stable_baselines3.common.monitor import Monitor


SERVER_ROOT = Path(__file__).resolve().parents[2]


def find_project_root() -> Path:
    candidates = [
        SERVER_ROOT.parent,
        SERVER_ROOT.parent.parent,
        Path("/Users/inje/develop/projects/capstone_main"),
    ]
    for candidate in candidates:
        if (candidate / "ai_module/scripts/paper_repro").exists():
            return candidate
    raise RuntimeError("Could not locate capstone_main project root with ai_module.")


PROJECT_ROOT = find_project_root()
PAPER_REPRO = PROJECT_ROOT / "ai_module/scripts/paper_repro"
AI_REPO = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_REPO))
sys.path.insert(0, str(PROJECT_ROOT / "ai_module/scripts"))
sys.path.insert(0, str(PAPER_REPRO))

import compare_five_methods_asym525 as cmp  # noqa: E402
import eval_contract_guarded_sharing as guarded  # noqa: E402
from app.team_runtime.evcs_runtime import (  # noqa: E402
    SYS_CFG,
    get_valid_real_dates,
    load_real_dataset,
    make_full_pi_sac_model,
)
from app.team_runtime.safety_shield import ShieldConfig  # noqa: E402
from eval_sharing_corrected_tariff import select_eval_dates  # noqa: E402
from train_eval_shared_pisac import (  # noqa: E402
    SharedUpperEnv,
    build_shield_configs,
    build_station_configs,
    configure_runtime,
    load_lower_agents,
    plan_pv_surplus,
    plan_soft_milp,
    plan_zero,
)


ASSET_JSON = SERVER_ROOT / "frontend/public/assets/operation-comparison/evonly_vmoderate_v2p90_pvess_multiseed.json"
ASSET_JS = SERVER_ROOT / "frontend/public/assets/operation-comparison/evonly_vmoderate_v2p90_pvess_multiseed.js"
CORRECTED = PROJECT_ROOT / (
    "ai_module/artifacts/sharing_3arm/forecast_observation/"
    "corrected_tariff_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42.json"
)
FIVE_METHOD = PROJECT_ROOT / (
    "ai_module/artifacts/sharing_3arm/forecast_observation/"
    "five_method_comparison_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42_physical_oracle.json"
)


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def round3(value: float) -> float:
    return round(float(value), 3)


def trace_rollout(env: SharedUpperEnv, test_dates: list[str], name: str, policy) -> dict:
    traces: dict[str, list[float]] = {}
    monthly_station_peaks: dict[str, np.ndarray] = defaultdict(lambda: np.zeros(SYS_CFG.n_station, dtype=np.float64))
    grid_total = 0.0

    if isinstance(env, guarded.ContractGuardedSharedUpperEnv):
        env.reset_guard_state()

    for date in test_dates:
        env.day_data = env._build_day(date, fixed_soc=0.5)
        env.teacher_share_plan = env.teacher_plan_fn(env.day_data) if env.teacher_plan_fn is not None else None
        if name == "soft_milp_lower_pisac":
            env.share_plan = plan_soft_milp(env.day_data)
        elif name == "pv_surplus_lower_pisac":
            env.share_plan = plan_pv_surplus(env.day_data)
        elif name == "zero_share_lower_pisac":
            env.share_plan = plan_zero(env.day_data)
        else:
            env.share_plan = None

        env.soc = env.day_data["init_soc"].astype(np.float32).copy()
        env.grid_peak = np.zeros(SYS_CFG.n_station, dtype=np.float32)
        env.zero_grid_peak = np.zeros(SYS_CFG.n_station, dtype=np.float32)
        env.t = 0
        obs = env._obs()

        day_grid_by_station = []
        day_grid_total = []
        for _ in range(24):
            raw = policy(obs)
            obs, _, terminated, _, info = env.step(raw)
            grid_by_station = np.asarray(info["grid_by_station"], dtype=np.float64)
            day_grid_by_station.append(grid_by_station)
            total = float(np.sum(grid_by_station))
            day_grid_total.append(total)
            grid_total += total
            if terminated:
                break

        grid_arr = np.vstack(day_grid_by_station)
        month = str(pd.Timestamp(date).to_period("M"))
        monthly_station_peaks[month] = np.maximum(monthly_station_peaks[month], grid_arr.max(axis=0))
        traces[str(date)] = day_grid_total

    return {
        "traces": traces,
        "grid_total": float(grid_total),
        "monthly_station_peaks": {
            month: values.astype(float)
            for month, values in monthly_station_peaks.items()
        },
    }


def collect_sac_traces(corrected: dict) -> tuple[dict[str, dict[str, list[float]]], dict[str, float]]:
    meta = corrected["meta"]
    seeds = [int(seed) for seed in meta["seeds"]]
    test_csv = project_path(meta["test_csv"])
    ess_cap = float(meta["ess_cap_per_station"])
    peak_limit = float(meta["peak_limit_per_station"])
    ess_caps = tuple(float(x) for x in meta["ess_caps_per_station"])
    peak_limits = tuple(float(x) for x in meta["peak_limits_per_station"])
    share_max = float(meta["share_max_per_station"])

    configure_runtime(test_csv, ess_cap, peak_limit, share_max)
    station_configs = build_station_configs(ess_caps, peak_limits, ess_cap, peak_limit, SYS_CFG.n_station)
    shield_configs = build_shield_configs(station_configs)
    test_df = load_real_dataset(str(test_csv.resolve()))
    test_dates = select_eval_dates(
        get_valid_real_dates(test_df),
        eval_days=int(meta["eval_days"]),
        start_date=meta.get("start_date"),
        end_date=meta.get("end_date"),
    )
    shield = ShieldConfig(
        peak_limit_kwh=peak_limit,
        ess_capacity_kwh=ess_cap,
        ess_max_ratio_per_step=0.10,
        soc_min=0.1,
        soc_max=0.9,
        soc_low_reserve_threshold=0.3,
        future_horizon_hours=6,
    )

    per_method_seed_traces: dict[str, list[dict[str, list[float]]]] = {
        "localSac": [],
        "softMilp": [],
        "sharedSac": [],
    }
    per_method_totals: dict[str, list[float]] = {key: [] for key in per_method_seed_traces}

    for seed in seeds:
        print(f"replaying SAC seed={seed}", flush=True)
        lower_dir = guarded.resolve_artifact(meta["lower_dir_template"], seed)
        shared_dir = guarded.resolve_artifact(meta["shared_dir_template"], seed)
        model_meta = guarded.load_meta(shared_dir)
        teacher_plan_fn = guarded.teacher_plan_from_meta(model_meta)
        lower_agents = load_lower_agents(
            lower_dir,
            SYS_CFG.n_station,
            shield,
            station_configs=station_configs,
            shield_configs=shield_configs,
            lower_obs_mode=str(model_meta.get("lower_obs_mode", "basic")),
            obs_source=str(model_meta.get("obs_source", "actual")),
        )

        model_env = guarded.make_env(
            env_cls=SharedUpperEnv,
            test_df=test_df,
            test_dates=test_dates,
            lower_agents=lower_agents,
            shield=shield,
            station_configs=station_configs,
            shield_configs=shield_configs,
            teacher_plan_fn=teacher_plan_fn,
            meta=model_meta,
            paper_degradation=bool(meta.get("paper_degradation", False)),
        )
        upper_model = make_full_pi_sac_model(Monitor(model_env), name=f"operation_trace_upper_seed{seed}")
        for key, value in model_meta.items():
            if key in {
                "residual_milp",
                "residual_scale",
                "share_projection",
                "upper_reward_mode",
                "upper_obs_mode",
                "marginal_peak_worsen_penalty_krw_per_kwh",
                "marginal_soc_drawdown_penalty_krw_per_kwh",
                "pv_load_match_penalty_krw_per_kwh",
                "netload_smoothing_penalty_krw_per_kwh",
                "obs_source",
                "lower_obs_mode",
            }:
                setattr(upper_model, key, value)
        upper_model.load(str(shared_dir / "upper_SHARED_FULL.pt"))

        base_env = guarded.make_env(
            env_cls=SharedUpperEnv,
            test_df=test_df,
            test_dates=test_dates,
            lower_agents=lower_agents,
            shield=shield,
            station_configs=station_configs,
            shield_configs=shield_configs,
            teacher_plan_fn=teacher_plan_fn,
            meta=model_meta,
            paper_degradation=bool(meta.get("paper_degradation", False)),
        )
        local = trace_rollout(
            base_env,
            test_dates,
            "zero_share_lower_pisac",
            lambda _obs: np.zeros(SYS_CFG.n_station, dtype=np.float32),
        )
        soft = trace_rollout(
            base_env,
            test_dates,
            "soft_milp_lower_pisac",
            lambda _obs: np.zeros(SYS_CFG.n_station, dtype=np.float32),
        )

        guard_env = guarded.make_env(
            env_cls=guarded.ContractGuardedSharedUpperEnv,
            test_df=test_df,
            test_dates=test_dates,
            lower_agents=lower_agents,
            shield=shield,
            station_configs=station_configs,
            shield_configs=shield_configs,
            teacher_plan_fn=teacher_plan_fn,
            meta=model_meta,
            paper_degradation=bool(meta.get("paper_degradation", False)),
            monthly_reference_peaks=local["monthly_station_peaks"],
            guard_ratio=float(meta.get("guard_ratio", 1.0)),
            guard_margin_kw=float(meta.get("guard_margin_kw", 0.0)),
            net_guard=str(meta.get("net_guard", "none")),
            net_guard_slack_krw=float(meta.get("net_guard_slack_krw", 0.0)),
            tariff_guard_rate=float(meta.get("tariff_guard_rate", 0.0)),
            search_iterations=int(meta.get("search_iterations", 6)),
        )
        shared = trace_rollout(
            guard_env,
            test_dates,
            "shared_pisac",
            lambda obs: upper_model.predict(obs, deterministic=True)[0],
        )

        for key, result in (("localSac", local), ("softMilp", soft), ("sharedSac", shared)):
            per_method_seed_traces[key].append(result["traces"])
            per_method_totals[key].append(float(result["grid_total"]))

    averaged: dict[str, dict[str, list[float]]] = {}
    totals: dict[str, float] = {}
    for method, traces in per_method_seed_traces.items():
        averaged[method] = {}
        dates = sorted(traces[0].keys())
        for date in dates:
            arr = np.array([seed_trace[date] for seed_trace in traces], dtype=float)
            averaged[method][date] = [round3(x) for x in arr.mean(axis=0)]
        totals[method] = float(np.mean(per_method_totals[method]))
    return averaged, totals


def direct_baseline_traces(days: list[dict]) -> tuple[dict[str, dict[str, list[float]]], dict[str, float]]:
    traces = {"gridOnly": {}, "default": {}}
    totals = {"gridOnly": 0.0, "default": 0.0}
    for day in days:
        grid_only = day["demand"].sum(axis=0)
        default = np.maximum(0.0, day["demand"] - day["pv"]).sum(axis=0)
        traces["gridOnly"][day["date"]] = [round3(x) for x in grid_only]
        traces["default"][day["date"]] = [round3(x) for x in default]
        totals["gridOnly"] += float(np.sum(grid_only))
        totals["default"] += float(np.sum(default))
    return traces, totals


def build_display_days(
    data_path: Path,
    *,
    eval_days: int,
    start_date: str | None,
    end_date: str | None,
) -> dict[str, dict]:
    df = pd.read_csv(data_path)
    selected_dates = cmp.select_dates(
        [str(date) for date in sorted(df["date"].unique())],
        eval_days=eval_days,
        start_date=start_date,
        end_date=end_date,
    )
    out: dict[str, dict] = {}
    for date in selected_dates:
        day = df[df["date"] == date]
        pv = np.zeros((3, 24), dtype=float)
        pv_forecast = np.zeros((3, 24), dtype=float)
        demand = np.zeros((3, 24), dtype=float)
        demand_forecast = np.zeros((3, 24), dtype=float)
        demand_p90 = np.zeros((3, 24), dtype=float)
        tou = np.zeros(24, dtype=float)
        for i in range(3):
            station = day[day["station"] == i].sort_values("hour")
            if len(station) != 24:
                raise ValueError(f"incomplete station day date={date} station={i}")
            pv[i] = station["pv_actual"].to_numpy(dtype=float)
            pv_forecast[i] = station["pv_forecast"].to_numpy(dtype=float)
            demand[i] = cmp.shift_24(station["demand_actual"].to_numpy(dtype=float), cmp.DEMAND_SHIFTS[i])
            demand_forecast[i] = cmp.shift_24(
                station["demand_forecast"].to_numpy(dtype=float),
                cmp.DEMAND_SHIFTS[i],
            )
            demand_p90[i] = cmp.shift_24(station["demand_p90"].to_numpy(dtype=float), cmp.DEMAND_SHIFTS[i])
            if i == 0:
                tou = station["tou"].to_numpy(dtype=float)
        out[str(date)] = {
            "pv": pv,
            "pv_forecast": pv_forecast,
            "demand": demand,
            "demand_forecast": demand_forecast,
            "demand_p90": demand_p90,
            "tou": tou,
        }
    return out


def forecast_rolling_milp_trace(
    days: list[dict],
    *,
    ess_efficiency_rt: float,
    terminal_soc_fixed: bool,
    objective: str,
    demand_forecast_scale: float,
    pv_forecast_scale: float,
) -> tuple[dict[str, list[float]], float]:
    traces: dict[str, list[float]] = {}
    total_grid = 0.0
    monthly_station_peaks: dict[str, np.ndarray] = defaultdict(lambda: np.zeros(3, dtype=float))
    for day in days:
        plan = cmp._solve_day_ahead_milp(
            day,
            current_month_peak=monthly_station_peaks[day["month"]],
            ess_efficiency_rt=ess_efficiency_rt,
            terminal_soc_fixed=terminal_soc_fixed,
            objective=objective,
            demand_forecast_scale=demand_forecast_scale,
            pv_forecast_scale=pv_forecast_scale,
        )
        hourly = []
        for t in range(24):
            proposed = plan["share"][:, t]
            export_cap = np.minimum(cmp.SHARE_MAX, np.maximum(0.0, day["pv"][:, t] + plan["dis"][:, t]))
            import_need = np.maximum(
                0.0,
                day["demand"][:, t] + plan["chg"][:, t] - day["pv"][:, t] - plan["dis"][:, t],
            )
            import_cap = np.minimum(cmp.SHARE_MAX, import_need)
            share = cmp._project_balanced_share(proposed, export_cap=export_cap, import_cap=import_cap)
            share_in = np.maximum(0.0, share)
            share_out = np.maximum(0.0, -share)
            grid_by_station = []
            for i in range(3):
                grid = max(
                    0.0,
                    day["demand"][i, t]
                    + plan["chg"][i, t]
                    + share_out[i]
                    - day["pv"][i, t]
                    - plan["dis"][i, t]
                    - share_in[i],
                )
                grid_by_station.append(grid)
                monthly_station_peaks[day["month"]][i] = max(monthly_station_peaks[day["month"]][i], grid)
            total = float(np.sum(grid_by_station))
            hourly.append(round3(total))
            total_grid += total
        traces[day["date"]] = hourly
    return traces, total_grid


def milp_milp_oracle_trace(
    days: list[dict],
    *,
    ess_efficiency_rt: float,
    terminal_soc_fixed: bool,
    objective: str,
) -> tuple[dict[str, list[float]], float]:
    n, horizon = 3, 24
    eff = float(np.sqrt(ess_efficiency_rt))
    ess_power = [cap * 0.10 for cap in cmp.ESS_CAP]
    months = sorted({day["month"] for day in days})

    prob = pulp.LpProblem("operation_trace_milp_milp_tariff_oracle", pulp.LpMinimize)
    chg = {}
    dis = {}
    soc = {}
    grid = {}
    curtail = {}
    share_in = {}
    share_out = {}
    monthly_peak = {
        (m, i): pulp.LpVariable(f"monthly_peak_{m}_{i}", lowBound=0.0)
        for m in months for i in range(n)
    }

    for d, day in enumerate(days):
        for i in range(n):
            for t in range(horizon):
                chg[(d, t, i)] = pulp.LpVariable(f"chg_{d}_{t}_{i}", 0.0, ess_power[i])
                dis[(d, t, i)] = pulp.LpVariable(f"dis_{d}_{t}_{i}", 0.0, ess_power[i])
                grid[(d, t, i)] = pulp.LpVariable(f"grid_{d}_{t}_{i}", 0.0)
                curtail[(d, t, i)] = pulp.LpVariable(f"curtail_{d}_{t}_{i}", 0.0)
                share_in[(d, t, i)] = pulp.LpVariable(f"share_in_{d}_{t}_{i}", 0.0, cmp.SHARE_MAX)
                share_out[(d, t, i)] = pulp.LpVariable(f"share_out_{d}_{t}_{i}", 0.0, cmp.SHARE_MAX)
            for t in range(horizon + 1):
                soc[(d, t, i)] = pulp.LpVariable(f"soc_{d}_{t}_{i}", cmp.SOC_MIN, cmp.SOC_MAX)
            prob += soc[(d, 0, i)] == cmp.SOC0
            if terminal_soc_fixed:
                prob += soc[(d, horizon, i)] == cmp.SOC0

    for d, day in enumerate(days):
        pv = day["pv"]
        demand = day["demand"]
        for t in range(horizon):
            prob += pulp.lpSum(share_in[(d, t, i)] for i in range(n)) == pulp.lpSum(
                share_out[(d, t, i)] for i in range(n)
            )
            for i in range(n):
                prob += soc[(d, t + 1, i)] == soc[(d, t, i)] + (
                    chg[(d, t, i)] * eff - dis[(d, t, i)] / eff
                ) / cmp.ESS_CAP[i]
                prob += (
                    grid[(d, t, i)]
                    + float(pv[i, t])
                    + dis[(d, t, i)]
                    + share_in[(d, t, i)]
                    == float(demand[i, t])
                    + chg[(d, t, i)]
                    + share_out[(d, t, i)]
                    + curtail[(d, t, i)]
                )
                prob += share_out[(d, t, i)] <= float(pv[i, t]) + dis[(d, t, i)]
                prob += monthly_peak[(day["month"], i)] >= grid[(d, t, i)]

    net_objective = (
        pulp.lpSum(grid[(d, t, i)] * float(days[d]["tou"][t]) for d in range(len(days)) for t in range(horizon) for i in range(n))
        + pulp.lpSum((chg[(d, t, i)] + dis[(d, t, i)]) * cmp.DEG_PER_KWH for d in range(len(days)) for t in range(horizon) for i in range(n))
        + pulp.lpSum((share_in[(d, t, i)] + share_out[(d, t, i)]) * cmp.SHARE_TRANSFER_COST * float(days[d]["tou"][t]) for d in range(len(days)) for t in range(horizon) for i in range(n))
    )
    if objective == "net":
        prob += net_objective
    elif objective == "total_tariff":
        prob += net_objective + cmp.DEMAND_CHARGE_RATE * pulp.lpSum(
            monthly_peak[(m, i)] for m in months for i in range(n)
        )
    else:
        raise ValueError(f"unknown oracle objective: {objective}")

    print("solving MILP+MILP trace", flush=True)
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[prob.status] != "Optimal":
        raise RuntimeError(f"oracle status={pulp.LpStatus[prob.status]}")

    traces: dict[str, list[float]] = {}
    total_grid = 0.0
    for d, day in enumerate(days):
        hourly = []
        for t in range(horizon):
            value = float(sum(pulp.value(grid[(d, t, i)]) for i in range(n)))
            hourly.append(round3(value))
            total_grid += value
        traces[day["date"]] = hourly
    return traces, total_grid


def update_asset(
    asset: dict,
    traces: dict[str, dict[str, list[float]]],
    totals: dict[str, float],
    display_days: dict[str, dict],
) -> None:
    for day in asset["days"]:
        date = day["date"]
        display_day = display_days[date]
        pv_total = display_day["pv"].sum(axis=0)
        pv_forecast_total = display_day["pv_forecast"].sum(axis=0)
        demand_total = display_day["demand"].sum(axis=0)
        demand_forecast_total = display_day["demand_forecast"].sum(axis=0)
        demand_p90_total = display_day["demand_p90"].sum(axis=0)
        for hour in day["hours"]:
            idx = int(hour["hour"])
            hour["pvActual"] = round3(pv_total[idx])
            hour["pvForecast"] = round3(pv_forecast_total[idx])
            hour["evActual"] = round3(demand_total[idx])
            hour["evForecast"] = round3(demand_forecast_total[idx])
            hour["evP90"] = round3(demand_p90_total[idx])
            for method, method_trace in traces.items():
                if date in method_trace:
                    hour["grid"][method] = round3(method_trace[date][idx])

        day["totals"]["pvActual"] = round(float(np.sum(pv_total)), 1)
        day["totals"]["pvForecast"] = round(float(np.sum(pv_forecast_total)), 1)
        day["totals"]["evActual"] = round(float(np.sum(demand_total)), 1)
        day["totals"]["evForecast"] = round(float(np.sum(demand_forecast_total)), 1)
        day["totals"]["defaultGrid"] = round(float(sum(h["grid"]["default"] for h in day["hours"])), 1)
        day["totals"]["sharedGrid"] = round(float(sum(h["grid"]["sharedSac"] for h in day["hours"])), 1)
        day["totals"]["milpGrid"] = round(float(sum(h["grid"]["milpMilp"] for h in day["hours"])), 1)

        for idx, station in enumerate(day.get("stations", [])):
            demand = display_day["demand"][idx]
            station["pvActual"] = round(float(np.sum(display_day["pv"][idx])), 1)
            station["evActual"] = round(float(np.sum(demand)), 1)
            station["defaultGrid"] = round(float(np.sum(np.maximum(0.0, demand - display_day["pv"][idx]))), 1)
            station["peakDemand"] = round(float(np.max(demand)), 1)
            station["peakHour"] = int(np.argmax(demand))

        for idx, station in enumerate(day.get("stationDemandHours", [])):
            station["values"] = [round3(x) for x in display_day["demand"][idx]]
            station["forecastValues"] = [round3(x) for x in display_day["demand_forecast"][idx]]

    asset["meta"]["gridProfileNote"] = (
        "PV/EV actual and forecast values are aggregated directly from the experiment CSV by date/hour. "
        "Method grid curves are exact offline counterfactual traces: local/soft/shared SAC are the "
        "seed 1/2/42 checkpoint replay mean, Forecast MILP is forecast-plan actual settlement, "
        "and MILP+MILP is the physical total-tariff oracle solve."
    )
    asset["meta"]["stationDemandNote"] = (
        "Station-level EV curves are date/hour values from the EV-only volume_moderate shift048 scenario CSV; "
        "solid lines show demand_actual and dashed lines show demand_forecast after the configured station shifts."
    )
    asset["meta"]["gridTraceSource"] = {
        "generatedBy": "server/scripts/ai/build_operation_grid_traces.py",
        "correctedTariffArtifact": str(CORRECTED.relative_to(PROJECT_ROOT)),
        "fiveMethodArtifact": str(FIVE_METHOD.relative_to(PROJECT_ROOT)),
        "sacTrace": "3-seed mean checkpoint replay with contract guard",
        "milpTrace": "CBC LP/MILP solve using five-method artifact options",
        "gridKwhByTrace": {key: round3(value) for key, value in sorted(totals.items())},
    }
    asset["meta"]["dashboardReplayPolicy"] = (
        "Map/MQTT replay remains a representative seed1-style sharing animation; "
        "operation-detail Grid curves use recomputed per-hour counterfactual traces."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-json", type=Path, default=ASSET_JSON)
    parser.add_argument("--asset-js", type=Path, default=ASSET_JS)
    parser.add_argument("--corrected", type=Path, default=CORRECTED)
    parser.add_argument("--five-method", type=Path, default=FIVE_METHOD)
    args = parser.parse_args()

    corrected = json.loads(project_path(args.corrected).read_text())
    five_method = json.loads(project_path(args.five_method).read_text())
    five_meta = five_method["meta"]
    cmp.ESS_CAP = tuple(float(x) for x in five_meta["ess_cap"])
    cmp.PEAK_LIMIT = tuple(float(x) for x in five_meta["peak_limit"])

    days = cmp.build_days(
        project_path(five_meta["test_csv"]),
        eval_days=int(five_meta["eval_days"]),
        start_date=five_meta.get("start_date"),
        end_date=five_meta.get("end_date"),
    )
    oracle_eff_rt, oracle_terminal_soc_fixed = cmp.oracle_physics_defaults(five_meta["oracle_physics"])

    direct_traces, direct_totals = direct_baseline_traces(days)
    sac_traces, sac_totals = collect_sac_traces(corrected)
    print("solving Forecast MILP trace", flush=True)
    forecast_trace, forecast_total = forecast_rolling_milp_trace(
        days,
        ess_efficiency_rt=oracle_eff_rt,
        terminal_soc_fixed=oracle_terminal_soc_fixed,
        objective=five_meta["forecast_rolling_milp"],
        demand_forecast_scale=float(five_meta["forecast_rolling_demand_scale"]),
        pv_forecast_scale=float(five_meta["forecast_rolling_pv_scale"]),
    )
    milp_trace, milp_total = milp_milp_oracle_trace(
        days,
        ess_efficiency_rt=oracle_eff_rt,
        terminal_soc_fixed=oracle_terminal_soc_fixed,
        objective="total_tariff",
    )

    traces = {
        **direct_traces,
        **sac_traces,
        "forecastMilp": forecast_trace,
        "milpMilp": milp_trace,
    }
    totals = {
        **direct_totals,
        **sac_totals,
        "forecastMilp": forecast_total,
        "milpMilp": milp_total,
    }

    asset_path = args.asset_json if args.asset_json.is_absolute() else SERVER_ROOT / args.asset_json
    js_path = args.asset_js if args.asset_js.is_absolute() else SERVER_ROOT / args.asset_js
    asset = json.loads(asset_path.read_text())
    display_days = build_display_days(
        project_path(five_meta["test_csv"]),
        eval_days=int(five_meta["eval_days"]),
        start_date=five_meta.get("start_date"),
        end_date=five_meta.get("end_date"),
    )
    update_asset(asset, traces, totals, display_days)
    asset_path.write_text(json.dumps(asset, ensure_ascii=False, indent=2))
    js_path.write_text("window.operationComparisonData = " + json.dumps(asset, ensure_ascii=False, separators=(",", ":")) + ";")

    for key in ["gridOnly", "default", "localSac", "softMilp", "sharedSac", "forecastMilp", "milpMilp"]:
        print(f"{key}: {totals[key]:.1f} kWh", flush=True)
    print(f"WROTE {asset_path}", flush=True)
    print(f"WROTE {js_path}", flush=True)


if __name__ == "__main__":
    main()
