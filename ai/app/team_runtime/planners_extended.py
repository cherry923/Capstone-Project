"""Extended upper planners for the C-category architectural probes.

These planners are NOT the production planner; they live in a separate module
so that probe scripts can A/B them against the manifest-loaded MILP planner
without rewriting the production pipeline.

Stage 1: SoftPeakSlackMILPPlanner — 2-stage lexicographic MILP that
    elastically penalizes peak limit violations in the plan itself.
Stage 2: QuantileSafetyMILPPlanner — Stage 1 + uses the demand p90 forecast
    as a one-sided chance constraint surrogate.

Codex 2026-05-19 토론 그대로 (`ev_full_investigation_report_2026-05-19.md`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pulp

from app.team_runtime.evcs_runtime import ST_CFG, SYS_CFG


@dataclass
class PlanResult:
    share: np.ndarray  # shape (T, n)
    grid_plan: np.ndarray  # shape (T, n), planned grid kWh (for reporting)
    peak_slack: np.ndarray  # shape (T, n)
    quantile_slack: Optional[np.ndarray]
    status: str
    objective_stage1: float
    objective_stage2: float


class SoftPeakSlackMILPPlanner:
    """C2-soft: peak limit as elastic constraint with 2-stage lexicographic MILP.

    Stage 1: minimize total peak_slack (i.e., put peak_limit as priority).
    Stage 2: minimize grid_cost + transfer_cost s.t. total slack ≤ stage1 + epsilon.

    If either stage solver fails, returns zero-share baseline plan and marks
    status accordingly (artifact-visible).
    """

    def __init__(
        self,
        peak_limit_kwh: Optional[float] = None,
        share_abs_max_kwh: Optional[float] = None,
        share_transfer_cost: Optional[float] = None,
        slack_epsilon: float = 1.0,
        peak_slack_unit_penalty_stage2: float = 0.0,
    ) -> None:
        self.peak_limit = float(peak_limit_kwh if peak_limit_kwh is not None else ST_CFG.peak_limit_kwh)
        self.share_max = float(share_abs_max_kwh if share_abs_max_kwh is not None else SYS_CFG.share_abs_max_kwh)
        self.transfer_cost = float(share_transfer_cost if share_transfer_cost is not None else SYS_CFG.share_transfer_cost)
        self.slack_epsilon = float(slack_epsilon)
        self.peak_slack_penalty_stage2 = float(peak_slack_unit_penalty_stage2)

    def plan(self, day_data: Dict) -> PlanResult:
        n, T = SYS_CFG.n_station, SYS_CFG.horizon
        tou = day_data["tou"]
        pv_f = np.stack([day_data["stations"][i]["pv_forecast"] for i in range(n)], axis=0)
        dm_f = np.stack([day_data["stations"][i]["demand_forecast"] for i in range(n)], axis=0)
        share_max = float(day_data.get("share_abs_max_kwh") or self.share_max)
        station_config = day_data.get("station_config")
        peak_limit = float(getattr(station_config, "peak_limit_kwh", self.peak_limit))

        stage1_total_slack, share_s1, grid_s1, slack_s1, status1 = self._solve_stage1(T, n, tou, pv_f, dm_f, share_max, peak_limit)
        if status1 != "Optimal":
            return self._zero_share_fallback(T, n, status1, status1)

        share_s2, grid_s2, slack_s2, obj_s2, status2 = self._solve_stage2(
            T, n, tou, pv_f, dm_f,
            stage1_total_slack=stage1_total_slack,
            share_max=share_max,
            peak_limit=peak_limit,
        )
        if status2 != "Optimal":
            return self._zero_share_fallback(T, n, status1, status2)

        return PlanResult(
            share=share_s2,
            grid_plan=grid_s2,
            peak_slack=slack_s2,
            quantile_slack=None,
            status=f"stage1={status1};stage2={status2}",
            objective_stage1=float(stage1_total_slack),
            objective_stage2=float(obj_s2),
        )

    def _solve_stage1(self, T, n, tou, pv_f, dm_f, share_max: float, peak_limit: float):
        prob = pulp.LpProblem("upper_milp_stage1_min_peak_slack", pulp.LpMinimize)
        share = pulp.LpVariable.dicts(
            "share", ((t, i) for t in range(T) for i in range(n)),
            lowBound=-share_max, upBound=share_max, cat="Continuous",
        )
        grid = pulp.LpVariable.dicts(
            "grid", ((t, i) for t in range(T) for i in range(n)),
            lowBound=0.0, cat="Continuous",
        )
        slack = pulp.LpVariable.dicts(
            "peak_slack", ((t, i) for t in range(T) for i in range(n)),
            lowBound=0.0, cat="Continuous",
        )
        prob += pulp.lpSum(slack[(t, i)] for t in range(T) for i in range(n))
        for t in range(T):
            prob += pulp.lpSum(share[(t, i)] for i in range(n)) == 0.0
            for i in range(n):
                prob += grid[(t, i)] + pv_f[i, t] + share[(t, i)] >= dm_f[i, t]
                prob += grid[(t, i)] <= peak_limit + slack[(t, i)]
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        status = pulp.LpStatus[prob.status]
        if status != "Optimal":
            return 0.0, None, None, None, status
        total_slack = float(sum(float(slack[(t, i)].value()) for t in range(T) for i in range(n)))
        return total_slack, share, grid, slack, status

    def _solve_stage2(self, T, n, tou, pv_f, dm_f, stage1_total_slack: float, share_max: float, peak_limit: float):
        prob = pulp.LpProblem("upper_milp_stage2_min_cost", pulp.LpMinimize)
        share = pulp.LpVariable.dicts(
            "share", ((t, i) for t in range(T) for i in range(n)),
            lowBound=-share_max, upBound=share_max, cat="Continuous",
        )
        grid = pulp.LpVariable.dicts(
            "grid", ((t, i) for t in range(T) for i in range(n)),
            lowBound=0.0, cat="Continuous",
        )
        share_abs = pulp.LpVariable.dicts(
            "share_abs", ((t, i) for t in range(T) for i in range(n)),
            lowBound=0.0, cat="Continuous",
        )
        slack = pulp.LpVariable.dicts(
            "peak_slack", ((t, i) for t in range(T) for i in range(n)),
            lowBound=0.0, cat="Continuous",
        )
        prob += pulp.lpSum(
            tou[t] * grid[(t, i)]
            + self.transfer_cost * tou[t] * share_abs[(t, i)]
            + self.peak_slack_penalty_stage2 * slack[(t, i)]
            for t in range(T) for i in range(n)
        )
        prob += pulp.lpSum(slack[(t, i)] for t in range(T) for i in range(n)) <= stage1_total_slack + self.slack_epsilon
        for t in range(T):
            prob += pulp.lpSum(share[(t, i)] for i in range(n)) == 0.0
            for i in range(n):
                prob += share_abs[(t, i)] >= share[(t, i)]
                prob += share_abs[(t, i)] >= -share[(t, i)]
                prob += grid[(t, i)] + pv_f[i, t] + share[(t, i)] >= dm_f[i, t]
                prob += grid[(t, i)] <= peak_limit + slack[(t, i)]
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        status = pulp.LpStatus[prob.status]
        if status != "Optimal":
            return None, None, None, None, status
        share_arr = np.zeros((T, n), dtype=np.float32)
        grid_arr = np.zeros((T, n), dtype=np.float32)
        slack_arr = np.zeros((T, n), dtype=np.float32)
        for t in range(T):
            for i in range(n):
                share_arr[t, i] = float(share[(t, i)].value())
                grid_arr[t, i] = float(grid[(t, i)].value())
                slack_arr[t, i] = float(slack[(t, i)].value())
        return share_arr, grid_arr, slack_arr, pulp.value(prob.objective), status

    def _zero_share_fallback(self, T, n, status1: str, status2: str) -> PlanResult:
        return PlanResult(
            share=np.zeros((T, n), dtype=np.float32),
            grid_plan=np.zeros((T, n), dtype=np.float32),
            peak_slack=np.zeros((T, n), dtype=np.float32),
            quantile_slack=None,
            status=f"FALLBACK_ZERO_SHARE; stage1={status1}; stage2={status2}",
            objective_stage1=float("nan"),
            objective_stage2=float("nan"),
        )


class QuantileSafetyMILPPlanner(SoftPeakSlackMILPPlanner):
    """C5(a): Stage 1 minimizes peak slack against the demand p90 forecast
    (deterministic surrogate for one-sided chance constraint at the 90% level),
    then Stage 2 keeps slack at stage1 + epsilon and minimizes expected cost
    on demand p50.

    For honesty in framing: this is NOT a full scenario-based stochastic MILP.
    The quantile p90 is used as a deterministic upper-bound surrogate; joint
    probability across hours and stations is not guaranteed at 90%.
    """

    def __init__(
        self,
        quantile_slack_unit_penalty_stage2: float = 0.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.quantile_slack_penalty_stage2 = float(quantile_slack_unit_penalty_stage2)

    def plan(self, day_data: Dict) -> PlanResult:
        """Use station demand_p90 when available; otherwise fall back to p50 soft-peak MILP."""
        stations = day_data.get("stations", [])
        if stations and all("demand_p90" in station for station in stations):
            demand_p90 = np.stack([station["demand_p90"] for station in stations], axis=0)
            return self.plan_with_quantile(day_data, demand_p90)
        return super().plan(day_data)

    def plan_with_quantile(self, day_data: Dict, demand_p90_per_station: np.ndarray) -> PlanResult:
        """`demand_p90_per_station` has shape (n_station, T) and is used in place
        of demand_forecast for the safety constraint, while the cost objective
        still uses demand_forecast (typically p50/mean).
        """
        n, T = SYS_CFG.n_station, SYS_CFG.horizon
        tou = day_data["tou"]
        pv_f = np.stack([day_data["stations"][i]["pv_forecast"] for i in range(n)], axis=0)
        dm_p50 = np.stack([day_data["stations"][i]["demand_forecast"] for i in range(n)], axis=0)
        share_max = float(day_data.get("share_abs_max_kwh") or self.share_max)
        station_config = day_data.get("station_config")
        peak_limit = float(getattr(station_config, "peak_limit_kwh", self.peak_limit))
        assert demand_p90_per_station.shape == dm_p50.shape, (
            f"expected demand_p90 shape {dm_p50.shape}, got {demand_p90_per_station.shape}"
        )

        stage1_total_slack, status1 = self._solve_stage1_quantile(T, n, tou, pv_f, dm_p50, demand_p90_per_station, share_max, peak_limit)
        if status1 != "Optimal":
            return self._zero_share_fallback(T, n, status1, status1)

        result = self._solve_stage2_quantile(
            T, n, tou, pv_f, dm_p50, demand_p90_per_station,
            stage1_total_slack=stage1_total_slack,
            share_max=share_max,
            peak_limit=peak_limit,
        )
        return result

    def _solve_stage1_quantile(self, T, n, tou, pv_f, dm_p50, dm_p90, share_max: float, peak_limit: float):
        prob = pulp.LpProblem("upper_milp_quantile_stage1", pulp.LpMinimize)
        share = pulp.LpVariable.dicts(
            "share", ((t, i) for t in range(T) for i in range(n)),
            lowBound=-share_max, upBound=share_max, cat="Continuous",
        )
        grid = pulp.LpVariable.dicts(
            "grid", ((t, i) for t in range(T) for i in range(n)),
            lowBound=0.0, cat="Continuous",
        )
        peak_slack = pulp.LpVariable.dicts(
            "peak_slack", ((t, i) for t in range(T) for i in range(n)),
            lowBound=0.0, cat="Continuous",
        )
        # Stage 1 minimizes total peak slack while the safety side is on demand_p90.
        prob += pulp.lpSum(peak_slack[(t, i)] for t in range(T) for i in range(n))
        for t in range(T):
            prob += pulp.lpSum(share[(t, i)] for i in range(n)) == 0.0
            for i in range(n):
                prob += grid[(t, i)] + pv_f[i, t] + share[(t, i)] >= dm_p90[i, t]
                prob += grid[(t, i)] <= peak_limit + peak_slack[(t, i)]
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        status = pulp.LpStatus[prob.status]
        if status != "Optimal":
            return 0.0, status
        total_slack = float(sum(float(peak_slack[(t, i)].value()) for t in range(T) for i in range(n)))
        return total_slack, status

    def _solve_stage2_quantile(self, T, n, tou, pv_f, dm_p50, dm_p90, stage1_total_slack: float, share_max: float, peak_limit: float):
        prob = pulp.LpProblem("upper_milp_quantile_stage2", pulp.LpMinimize)
        share = pulp.LpVariable.dicts(
            "share", ((t, i) for t in range(T) for i in range(n)),
            lowBound=-share_max, upBound=share_max, cat="Continuous",
        )
        grid_mean = pulp.LpVariable.dicts(
            "grid_mean", ((t, i) for t in range(T) for i in range(n)),
            lowBound=0.0, cat="Continuous",
        )
        grid_p90 = pulp.LpVariable.dicts(
            "grid_p90", ((t, i) for t in range(T) for i in range(n)),
            lowBound=0.0, cat="Continuous",
        )
        share_abs = pulp.LpVariable.dicts(
            "share_abs", ((t, i) for t in range(T) for i in range(n)),
            lowBound=0.0, cat="Continuous",
        )
        peak_slack = pulp.LpVariable.dicts(
            "peak_slack", ((t, i) for t in range(T) for i in range(n)),
            lowBound=0.0, cat="Continuous",
        )
        prob += pulp.lpSum(
            tou[t] * grid_mean[(t, i)]
            + self.transfer_cost * tou[t] * share_abs[(t, i)]
            + self.peak_slack_penalty_stage2 * peak_slack[(t, i)]
            for t in range(T) for i in range(n)
        )
        prob += pulp.lpSum(peak_slack[(t, i)] for t in range(T) for i in range(n)) <= stage1_total_slack + self.slack_epsilon
        for t in range(T):
            prob += pulp.lpSum(share[(t, i)] for i in range(n)) == 0.0
            for i in range(n):
                prob += share_abs[(t, i)] >= share[(t, i)]
                prob += share_abs[(t, i)] >= -share[(t, i)]
                # Expected supply constraint at p50
                prob += grid_mean[(t, i)] + pv_f[i, t] + share[(t, i)] >= dm_p50[i, t]
                # Safety constraint at p90
                prob += grid_p90[(t, i)] + pv_f[i, t] + share[(t, i)] >= dm_p90[i, t]
                prob += grid_p90[(t, i)] <= peak_limit + peak_slack[(t, i)]
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        status = pulp.LpStatus[prob.status]
        if status != "Optimal":
            return self._zero_share_fallback(T, n, "Optimal", status)
        share_arr = np.zeros((T, n), dtype=np.float32)
        grid_arr = np.zeros((T, n), dtype=np.float32)
        peak_slack_arr = np.zeros((T, n), dtype=np.float32)
        for t in range(T):
            for i in range(n):
                share_arr[t, i] = float(share[(t, i)].value())
                grid_arr[t, i] = float(grid_mean[(t, i)].value())
                peak_slack_arr[t, i] = float(peak_slack[(t, i)].value())
        return PlanResult(
            share=share_arr,
            grid_plan=grid_arr,
            peak_slack=peak_slack_arr,
            quantile_slack=peak_slack_arr.copy(),
            status=f"quantile_stage1=Optimal;stage2={status}",
            objective_stage1=float(stage1_total_slack),
            objective_stage2=float(pulp.value(prob.objective)),
        )
