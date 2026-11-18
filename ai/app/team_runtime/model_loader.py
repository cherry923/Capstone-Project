import json
from pathlib import Path
from typing import Dict, List, Any

from stable_baselines3 import SAC
from stable_baselines3.common.monitor import Monitor

from app.settings import TEAM_SAC_MODEL_PACKAGE_DIR
from app.team_runtime.evcs_runtime import (
    EXP_CFG,
    ST_CFG,
    SYS_CFG,
    SAC_CFG,
    PI_CFG,
    DefaultUpperPlanner,
    UpperMILPPlanner,
    DefaultLowerAgent,
    LowerStationEnv,
    UpperPlannerEnv,
    make_full_pi_sac_model,
)


class LoadedModelBundle:
    def __init__(self, manifest: Dict, upper_model: Any, lower_agents: List[Any], shield_config: Any = None):
        self.manifest = manifest
        self.upper_model = upper_model
        self.lower_agents = lower_agents
        self.shield_config = shield_config

    @property
    def model_id(self) -> str:
        return self.manifest["model_id"]

    @property
    def upper_algo(self) -> str:
        return self.manifest["algorithm"]["upper_algo"]

    @property
    def lower_algo(self) -> str:
        return self.manifest["algorithm"]["lower_algo"]


def _apply_manifest_config(manifest: Dict):
    env_cfg = manifest["environment"]
    train_cfg = manifest.get("training_params") or {}
    algo_cfg = manifest["algorithm"]

    for k, v in env_cfg["station_config"].items():
        setattr(ST_CFG, k, v)

    for k, v in env_cfg["system_config"].items():
        setattr(SYS_CFG, k, v)

    for k, v in (train_cfg.get("sac_params") or {}).items():
        setattr(SAC_CFG, k, v)

    for k, v in (train_cfg.get("pi_params") or {}).items():
        setattr(PI_CFG, k, v)

    EXP_CFG.upper_algo = algo_cfg["upper_algo"]
    EXP_CFG.lower_algo = algo_cfg["lower_algo"]
    EXP_CFG.use_independent_lower_agents = algo_cfg.get("independent_lower_agents", True)


def _make_lower_env_for_load(algo: str, station_idx, upper_for_training: str):
    if upper_for_training == "MILP":
        upper_planner = UpperMILPPlanner()
    elif upper_for_training == "DEFAULT":
        upper_planner = DefaultUpperPlanner()
    elif upper_for_training == "SOFT_PEAK_MILP":
        from app.team_runtime.planners_extended import SoftPeakSlackMILPPlanner
        upper_planner = SoftPeakSlackMILPPlanner()
    elif upper_for_training == "QUANTILE_SAFETY_MILP":
        from app.team_runtime.planners_extended import QuantileSafetyMILPPlanner
        upper_planner = QuantileSafetyMILPPlanner()
    else:
        upper_planner = None

    env = LowerStationEnv(
        station_idx=station_idx,
        upper_planner=upper_planner,
        pi_controller=None,
        bad_prediction=False,
    )
    return Monitor(env)


def _make_upper_env_for_load(lower_agents: List[Any]):
    env = UpperPlannerEnv(
        lower_agents=lower_agents,
        pi_controller=None,
        bad_prediction=False,
    )
    return Monitor(env)


def _load_lower_agent(meta: Dict, model_dir: Path, upper_for_training: str):
    algo = meta["algo"]

    if algo == "DEFAULT":
        return DefaultLowerAgent()

    station_idx = meta.get("station_idx")
    env = _make_lower_env_for_load(
        algo=algo,
        station_idx=station_idx,
        upper_for_training=upper_for_training,
    )

    if meta["type"] == "sb3_sac":
        return SAC.load(str(model_dir / meta["path"]), env=env)

    if meta["type"] == "full_pi_sac":
        model = make_full_pi_sac_model(env, name=f"loaded_lower_{algo}_{meta['index']}")
        model.load(str(model_dir / meta["path"]))
        return model

    raise ValueError(f"지원하지 않는 lower model type: {meta['type']}")


def _load_upper_model(meta: Dict, model_dir: Path, lower_agents: List[Any]):
    algo = meta["algo"]

    if algo == "DEFAULT":
        return DefaultUpperPlanner()

    if algo == "MILP":
        return UpperMILPPlanner()

    if algo == "SOFT_PEAK_MILP":
        from app.team_runtime.planners_extended import SoftPeakSlackMILPPlanner
        return SoftPeakSlackMILPPlanner(**(meta.get("params") or {}))

    if algo == "QUANTILE_SAFETY_MILP":
        from app.team_runtime.planners_extended import QuantileSafetyMILPPlanner
        return QuantileSafetyMILPPlanner(**(meta.get("params") or {}))

    env = _make_upper_env_for_load(lower_agents)

    if meta["type"] == "sb3_sac":
        return SAC.load(str(model_dir / meta["path"]), env=env)

    if meta["type"] == "full_pi_sac":
        model = make_full_pi_sac_model(env, name=f"loaded_upper_{algo}")
        model.load(str(model_dir / meta["path"]))
        return model

    raise ValueError(f"지원하지 않는 upper model type: {meta['type']}")


def _load_shield_config(manifest: Dict) -> Any:
    """Load ShieldConfig from manifest if present, else return None."""
    raw = manifest.get("shield_config")
    if raw is None:
        return None
    from app.team_runtime.safety_shield import ShieldConfig
    return ShieldConfig(
        peak_limit_kwh=float(raw.get("peak_limit_kwh", 450.0)),
        soc_min=float(raw.get("soc_min", 0.10)),
        soc_max=float(raw.get("soc_max", 0.90)),
        soc_low_reserve_threshold=float(raw.get("soc_low_reserve_threshold", 0.30)),
        ess_max_ratio_per_step=float(raw.get("ess_max_ratio_per_step", 0.10)),
        ess_capacity_kwh=float(raw.get("ess_capacity_kwh", 998.0)),
        future_horizon_hours=int(raw.get("future_horizon_hours", 6)),
    )


def load_model_bundle() -> LoadedModelBundle:
    model_dir = Path(TEAM_SAC_MODEL_PACKAGE_DIR)
    manifest_path = model_dir / "manifest.json"

    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json을 찾을 수 없습니다: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    _apply_manifest_config(manifest)

    upper_for_training = manifest["algorithm"].get("upper_for_training", "MILP")

    lower_agents = [
        _load_lower_agent(
            meta=m,
            model_dir=model_dir,
            upper_for_training=upper_for_training,
        )
        for m in manifest["model_files"]["lower_models"]
    ]

    upper_model = _load_upper_model(
        meta=manifest["model_files"]["upper_model"],
        model_dir=model_dir,
        lower_agents=lower_agents,
    )

    shield_config = _load_shield_config(manifest)

    return LoadedModelBundle(
        manifest=manifest,
        upper_model=upper_model,
        lower_agents=lower_agents,
        shield_config=shield_config,
    )
