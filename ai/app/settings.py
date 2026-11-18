from __future__ import annotations

import os
from pathlib import Path


AI_REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_EV_SAC_PAYLOAD_PATH = (
    AI_REPO_ROOT / "app" / "data" / "ev_hybrid_calendar_24h_blend_sac_payload.json"
)
# production decision default = share_milp_shield:
# SoftPeakSlackMILP upper planner + DefaultLowerAgent + C6 forecast-aware shield.
# v1 synthetic PI-SAC는 multi-station에서 OOD로 catastrophic violation → research/ablation 전용으로 강등.
# (Codex 2026-05-21 oracle-final-review 권고: production은 안정적 lower default 필요)
DEFAULT_TEAM_SAC_MODEL_PACKAGE_DIR = (
    AI_REPO_ROOT / "models" / "evcs_api_model_v4_share_milp_shield"
)
DEFAULT_TEAM_PV_MODEL_PACKAGE_DIR = (
    AI_REPO_ROOT / "models" / "han_tft_pv_incheon_20250506"
)

EV_SAC_PAYLOAD_PATH = Path(
    os.environ.get("EV_SAC_PAYLOAD_PATH", str(DEFAULT_EV_SAC_PAYLOAD_PATH))
)
TEAM_SAC_MODEL_PACKAGE_DIR = Path(
    os.environ.get("TEAM_SAC_MODEL_PACKAGE_DIR", str(DEFAULT_TEAM_SAC_MODEL_PACKAGE_DIR))
)
TEAM_PV_MODEL_PACKAGE_DIR = Path(
    os.environ.get("TEAM_PV_MODEL_PACKAGE_DIR", str(DEFAULT_TEAM_PV_MODEL_PACKAGE_DIR))
)
TEAM_SAC_ENABLED = os.environ.get("TEAM_SAC_ENABLED", "1").lower() not in {"0", "false", "no"}
TEAM_PV_ENABLED = os.environ.get("TEAM_PV_ENABLED", "1").lower() not in {"0", "false", "no"}

EV_STRICT_TARGET_DATE = os.environ.get("EV_STRICT_TARGET_DATE", "0").lower() in {"1", "true", "yes"}
EV_STRICT_MISMATCH_DAYS = int(os.environ.get("EV_STRICT_MISMATCH_DAYS", "365"))

DEFAULT_PV_CAPACITY_KWH = float(os.environ.get("DEFAULT_PV_CAPACITY_KWH", "1000.0"))
DEFAULT_ESS_CAPACITY_KWH = float(os.environ.get("DEFAULT_ESS_CAPACITY_KWH", "1500.0"))
DEFAULT_ESS_POWER_LIMIT_KWH = float(os.environ.get("DEFAULT_ESS_POWER_LIMIT_KWH", "150.0"))
DEFAULT_SHARE_LIMIT_KWH = float(os.environ.get("DEFAULT_SHARE_LIMIT_KWH", "120.0"))

SOC_MIN = float(os.environ.get("SOC_MIN", "0.2"))
SOC_RESERVE = float(os.environ.get("SOC_RESERVE", "0.3"))
SOC_TARGET = float(os.environ.get("SOC_TARGET", "0.7"))

# regional_virtual_hub scenario spec.
# The production EV payload is aggregate_key=jeju_total (peak ~3.7MW). Treating that
# regional demand as a single virtual hub requires station physics sized to it, not the
# single-charger spec (998kWh/450kW), which makes ev_scale=1.0 an invalid (power-limited
# infeasible) scenario. These values were validated by probe_regional_hub.py to satisfy the
# strict feasibility bar (all peak_relief_feasible, residual~0, soc/peak violation~0) at
# ev_scale=1.0 with the 3-hub demand split. (Codex 2026-05-21 hub-spec review)
# regional_virtual_hub interpretation: jeju aggregate demand (peak ~3.7MW) modeled as 3 large
# regional hubs, each carrying its demand-weighted share (~0.34/0.36/0.30). Each hub is sized for
# its own slice — this is the "keep 3 stations, partition + re-sweep" option (Codex 2026-05-21
# review); a true single-hub collapse (n_station=1) is left as future work.
#
# Sizing rationale (probe_regional_hub.py sweeps):
#   - Per-station spec must keep the shield feasible (residual~0, soc/peak violation~0) at
#     ev_scale=1.0 against the realistic worst: PV=0 (overcast) + the EV service's empirical p90
#     (now passed through as demand_p90, ~1.13x p50). p50*1.3 (every hour simultaneously +30%) was
#     rejected as an unrealistic worst that would force a >2x oversize.
#   - Codex flagged the earlier 24MWh/station (= 72MWh effective across 3) as oversized. 16MWh/
#     station (= 48MWh total) is the validated per-hub size at this worst case.
REGIONAL_VIRTUAL_HUB_SPEC = {
    "peak_limit_kwh": 850.0,
    "ess_capacity_kwh": 16000.0,
    "ess_max_ratio": 0.10,        # power = 1600 kWh/step
    "pv_capacity_kwh": 700.0,
    "vmax_kwh": 3200.0,
    "share_abs_max_kwh": 250.0,
    "soc_min": 0.10,
    "soc_max": 0.90,
}
