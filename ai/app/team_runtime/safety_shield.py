"""Forecast-aware safety shield (C6) — supervisory control layer on top of SAC.

Codex 2026-05-19: SAC가 낸 (a_ess, a_pv) action을 실행 전에 deterministic
projection으로 보정한다. forecast가 dispatch에 직접 들어가는 가장 안전한
경로다. SAC retrain 불필요.

Three projection rules (composable):
1. peak_relief: if p90 demand → grid > peak_limit, force ESS discharge up to
   physical and SoC limits.
2. preserve_for_future_peak: if next H hours p90 peak risk is high and SoC is
   near minimum, suppress ESS discharge now.
3. peak_suppress_charge: if charging would push grid past peak_limit, suppress
   ESS charge.

The shield projects (a_ess, a_pv) → (a_ess', a_pv') and returns the new pair
along with diagnostic info on which rule fired.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class ShieldConfig:
    peak_limit_kwh: float = 450.0
    soc_min: float = 0.10
    soc_max: float = 0.90
    soc_low_reserve_threshold: float = 0.30
    ess_max_ratio_per_step: float = 0.10
    ess_capacity_kwh: float = 998.0
    future_horizon_hours: int = 3
    future_peak_risk_threshold_kwh: float = 0.0
    enable_peak_relief: bool = True
    enable_preserve_for_future_peak: bool = True
    enable_peak_suppress_charge: bool = True


@dataclass
class ShieldResult:
    a_ess_original: float
    a_pv_original: float
    a_ess_shielded: float
    a_pv_shielded: float
    fired_rules: list[str] = field(default_factory=list)
    diagnostics: Dict[str, float] = field(default_factory=dict)


def _expected_grid_kwh(pv_kwh: float, demand_kwh: float, share_kwh: float, ess_action_signed: float, ess_capacity_kwh: float) -> float:
    """Approximate grid kWh given current state and an ESS action.

    Mirrors station_flow simplification: grid covers (demand - share_in + share_out)
    after pv and ESS discharge contribute. Charging adds to grid demand.
    """
    received = max(0.0, share_kwh)
    exported = max(0.0, -share_kwh)
    internal_demand = max(0.0, demand_kwh - received) + exported
    ess_energy = ess_action_signed * ess_capacity_kwh
    discharge = max(0.0, -ess_energy)
    charge = max(0.0, ess_energy)
    remaining_after_pv = max(0.0, internal_demand - pv_kwh - discharge)
    surplus_pv_after_demand = max(0.0, pv_kwh - internal_demand)
    grid_charge = max(0.0, charge - surplus_pv_after_demand)
    return remaining_after_pv + grid_charge


def shield_action(
    *,
    t: int,
    soc: float,
    pv_actual: float,
    demand_actual: float,
    demand_forecast_p50_24h: np.ndarray,
    demand_forecast_p90_24h: np.ndarray,
    share_kwh: float,
    sac_action: np.ndarray,
    config: ShieldConfig,
) -> ShieldResult:
    """Project SAC action under forecast-aware safety constraints."""
    a_ess_raw = float(np.clip(sac_action[0], -config.ess_max_ratio_per_step, config.ess_max_ratio_per_step))
    a_pv = float(np.clip(sac_action[1], 0.0, 1.0))
    a_ess = a_ess_raw

    fired: list[str] = []
    diag: Dict[str, float] = {}

    p90_now = float(demand_forecast_p90_24h[t]) if t < len(demand_forecast_p90_24h) else float(demand_actual)
    expected_grid_p90 = _expected_grid_kwh(pv_actual, p90_now, share_kwh, a_ess, config.ess_capacity_kwh)
    diag["expected_grid_p90_kwh"] = expected_grid_p90

    # current_peak_violation: a *present* p90 grid breach exists this step, regardless of whether
    # peak_relief actually changed the action (e.g. when the SAC is already discharging at the cap,
    # a_ess_relief == a_ess so peak_relief is not appended). preserve must never undo discharge
    # while a current breach is open.
    current_peak_violation = config.enable_peak_relief and expected_grid_p90 > config.peak_limit_kwh

    # Rule 1: peak_relief — if p90 grid > peak_limit, force discharge
    if current_peak_violation:
        deficit = expected_grid_p90 - config.peak_limit_kwh
        max_discharge_by_soc = max(0.0, soc - config.soc_min) * config.ess_capacity_kwh
        max_discharge_by_power = config.ess_max_ratio_per_step * config.ess_capacity_kwh
        physical_max = min(max_discharge_by_soc, max_discharge_by_power)
        delivered = min(deficit, physical_max)
        a_ess_relief = -delivered / config.ess_capacity_kwh  # signed action (negative = discharge)
        if a_ess_relief < a_ess:
            a_ess = a_ess_relief
            fired.append("peak_relief")
            diag["peak_relief_kwh"] = delivered
            # Feasibility: can the ESS physically cut the whole current violation?
            residual = max(0.0, deficit - delivered)
            diag["peak_residual_kwh"] = residual
            diag["peak_relief_feasible"] = 0.0 if residual > 1e-6 else 1.0
            if residual > 1e-6:
                # Distinguish the binding physical limit so callers can size the hub correctly.
                diag["peak_relief_binding"] = (
                    0.0 if max_discharge_by_soc <= max_discharge_by_power else 1.0
                )  # 0 = SoC-limited, 1 = power-limited

    # Rule 2: preserve_for_future_peak — if upcoming peak risk and SoC low, suppress discharge.
    # Contract: current peak safety is paramount. If peak_relief already forced a discharge to
    # cut a *current* violation, preserve must NOT undo it (otherwise the shield would re-expose
    # the present violation to protect a future one). Preserve only governs the agent's own
    # voluntary discharge, not relief-mandated discharge.
    if config.enable_preserve_for_future_peak and a_ess < 0 and not current_peak_violation:
        end = min(len(demand_forecast_p90_24h), t + 1 + config.future_horizon_hours)
        future_p90 = demand_forecast_p90_24h[t + 1 : end]
        future_peak_risk = float(np.maximum(0.0, future_p90 - config.peak_limit_kwh).sum())
        diag["future_peak_risk_kwh"] = future_peak_risk
        if soc < config.soc_low_reserve_threshold and future_peak_risk > config.future_peak_risk_threshold_kwh:
            a_ess = max(a_ess, 0.0)  # block discharge
            fired.append("preserve_for_future_peak")

    # Rule 3: peak_suppress_charge — if charging pushes grid past peak, suppress
    if config.enable_peak_suppress_charge and a_ess > 0:
        post_charge_grid_p90 = _expected_grid_kwh(pv_actual, p90_now, share_kwh, a_ess, config.ess_capacity_kwh)
        if post_charge_grid_p90 > config.peak_limit_kwh:
            zero_grid_p90 = _expected_grid_kwh(pv_actual, p90_now, share_kwh, 0.0, config.ess_capacity_kwh)
            if zero_grid_p90 < post_charge_grid_p90:
                a_ess = 0.0
                fired.append("peak_suppress_charge")

    # Rule 4: soc_projection (Codex 2026-05-22) — 최종 action은 항상 SoC-safe.
    # next_soc = soc + a_ess 가 [soc_min, soc_max] 안에 들도록 a_ess를 투영.
    # shield가 peak만 보고 SoC를 안 막던 문제(soc_violation 잔존)를 닫는다.
    soc_safe_low = config.soc_min - soc
    soc_safe_high = config.soc_max - soc
    a_ess_projected = float(min(max(a_ess, soc_safe_low), soc_safe_high))
    if abs(a_ess_projected - a_ess) > 1e-9:
        a_ess = a_ess_projected
        fired.append("soc_projection")
        diag["soc_projection_to"] = a_ess

    return ShieldResult(
        a_ess_original=a_ess_raw,
        a_pv_original=a_pv,
        a_ess_shielded=a_ess,
        a_pv_shielded=a_pv,
        fired_rules=fired,
        diagnostics=diag,
    )
