from typing import Dict, List, Any
import numpy as np

from app.team_runtime.evcs_runtime import SYS_CFG, ST_CFG, project_share, station_flow


PLAN_BASED_UPPERS = {"DEFAULT", "MILP", "SOFT_PEAK_MILP", "QUANTILE_SAFETY_MILP"}


def _upper_obs(t: int, soc: np.ndarray, day_data: Dict) -> np.ndarray:
    total_pv = sum(day_data["stations"][i]["pv_actual"][t] for i in range(SYS_CFG.n_station))
    total_dm = sum(day_data["stations"][i]["demand_actual"][t] for i in range(SYS_CFG.n_station))

    return np.array(
        [
            t / 23.0,
            total_pv / (ST_CFG.pv_capacity_kwh * SYS_CFG.n_station),
            total_dm / (ST_CFG.vmax_kwh * SYS_CFG.n_station),
            day_data["tou"][t] / SYS_CFG.tou_high,
            soc[0],
            soc[1],
            soc[2],
        ],
        dtype=np.float32,
    )


FORECAST_LOOKAHEAD = 6  # 미래 N시간 수요 lookahead (Codex: forecast-blind 해소)


def _forecast_lookahead(s: Dict, t: int) -> list:
    """다음 FORECAST_LOOKAHEAD 시간의 수요 예측(정규화). PI-SAC가 미래 피크를 보고
    SoC를 미리 보존할 수 있게 한다. p90 있으면 p90, 없으면 forecast 사용."""
    src = s.get("demand_p90")
    if src is None:
        src = s["demand_forecast"]
    out = []
    for k in range(1, FORECAST_LOOKAHEAD + 1):
        idx = t + k
        out.append(float(src[idx]) / ST_CFG.vmax_kwh if idx < len(src) else 0.0)
    return out


def _lower_obs(t: int, station_idx: int, soc_i: float, share_i: float, day_data: Dict) -> np.ndarray:
    s = day_data["stations"][station_idx]

    return np.array(
        [
            t / 23.0,
            soc_i,
            s["pv_actual"][t] / ST_CFG.pv_capacity_kwh,
            s["demand_actual"][t] / ST_CFG.vmax_kwh,
            day_data["tou"][t] / SYS_CFG.tou_high,
            share_i / SYS_CFG.share_abs_max_kwh,
            *_forecast_lookahead(s, t),
        ],
        dtype=np.float32,
    )


def run_inference_for_day(
    day_data: Dict,
    upper_algo: str,
    lower_algo: str,
    upper_model: Any,
    lower_agents: List[Any],
    shield_config: Any = None,
    station_config: Any = None,
) -> List[Dict]:
    if shield_config is not None:
        from app.team_runtime.safety_shield import shield_action

    # station_config (regional_virtual_hub scenario) overrides the global ST_CFG
    # physics spec for station_flow only; None keeps the default ST_CFG.
    station_config = station_config if station_config is not None else day_data.get("station_config")

    soc = day_data["init_soc"].copy()

    # share_abs_max also belongs to the scenario spec. DEFAULT upper emits zero share so it is
    # invisible today, but a SAC/PI-SAC upper must scale share by the scenario's limit, not the
    # global SYS_CFG, or spec and runtime diverge (Codex 2026-05-21 review).
    share_abs_max = day_data.get("share_abs_max_kwh") or SYS_CFG.share_abs_max_kwh

    if upper_algo in PLAN_BASED_UPPERS:
        plan_result = upper_model.plan(day_data)
        share_plan = getattr(plan_result, "share", plan_result)
    else:
        share_plan = None

    rows = []

    for t in range(SYS_CFG.horizon):
        if upper_algo in PLAN_BASED_UPPERS:
            share_t = share_plan[t]
        else:
            obs_upper = _upper_obs(t, soc, day_data)
            raw_share, _ = upper_model.predict(obs_upper, deterministic=True)
            share_t = project_share(
                raw_share=np.asarray(raw_share) * share_abs_max,
                share_max=share_abs_max,
            )

        for i in range(SYS_CFG.n_station):
            agent = lower_agents[i] if len(lower_agents) > 1 else lower_agents[0]

            lower_obs = _lower_obs(
                t=t,
                station_idx=i,
                soc_i=float(soc[i]),
                share_i=float(share_t[i]),
                day_data=day_data,
            )
            lower_action, _ = agent.predict(lower_obs, deterministic=True)

            s = day_data["stations"][i]

            shield_fired: list[str] = []
            shield_diag: Dict[str, float] = {}
            if shield_config is not None:
                p90 = s.get("demand_p90")
                if p90 is None:
                    p90 = np.asarray(s["demand_forecast"]) * 1.3
                sr = shield_action(
                    t=t, soc=float(soc[i]),
                    pv_actual=float(s["pv_actual"][t]),
                    demand_actual=float(s["demand_actual"][t]),
                    demand_forecast_p50_24h=s["demand_forecast"],
                    demand_forecast_p90_24h=p90,
                    share_kwh=float(share_t[i]),
                    sac_action=lower_action,
                    config=shield_config,
                )
                lower_action = np.array([sr.a_ess_shielded, sr.a_pv_shielded], dtype=np.float32)
                shield_fired = list(sr.fired_rules)
                shield_diag = dict(sr.diagnostics)

            flow = station_flow(
                soc=float(soc[i]),
                pv_t=float(s["pv_actual"][t]),
                demand_t=float(s["demand_actual"][t]),
                tou_t=float(day_data["tou"][t]),
                share_t_i=float(share_t[i]),
                action=lower_action,
                cfg=station_config,
            )

            rows.append({
                "date": day_data.get("date", "unknown"),
                "t": int(t),
                "station": int(i),
                "soc_before": float(soc[i]),
                "soc_after": float(flow["next_soc"]),
                "pv_actual": float(s["pv_actual"][t]),
                "demand_actual": float(s["demand_actual"][t]),
                "tou": float(day_data["tou"][t]),
                "share": float(share_t[i]),
                "a_ess": float(flow["a_ess"]),
                "a_pv": float(flow["a_pv"]),
                "grid_total_kwh": float(flow["grid_total_kwh"]),
                "grid_cost": float(flow["grid_cost"]),
                "self_supply_kwh": float(flow["self_supply_kwh"]),
                "loss_kwh": float(flow["loss_kwh"]),
                "peak_violation": float(flow["peak_violation"]),
                "soc_violation": float(flow["soc_violation"]),
                "objective_reward": float(flow["objective_reward"]),
                "shield_fired": shield_fired,
                "shield_diag": shield_diag,
            })

            soc[i] = flow["next_soc"]

    return rows
