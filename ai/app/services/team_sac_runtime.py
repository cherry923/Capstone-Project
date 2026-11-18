from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.settings import TEAM_SAC_ENABLED, TEAM_SAC_MODEL_PACKAGE_DIR


class TeamSACRuntimeUnavailable(RuntimeError):
    """Raised when the teammate model package cannot be loaded locally."""


@dataclass
class TeamSACResult:
    rows: list[dict[str, Any]]
    manifest: dict[str, Any]


class TeamSACDecisionRuntime:
    """Lazy adapter for Lee Jeonghyun's MILP + PI-SAC model package.

    The imported runtime depends on PyTorch, Stable-Baselines3, Gymnasium, and
    PuLP. Keeping imports lazy lets the lightweight contract endpoints and unit
    tests run even before the heavy decision environment is installed.
    """

    _bundle: Any | None = None

    def run(self, day_data: dict[str, Any]) -> TeamSACResult:
        if not TEAM_SAC_ENABLED:
            raise TeamSACRuntimeUnavailable("TEAM_SAC_ENABLED is disabled")
        if not TEAM_SAC_MODEL_PACKAGE_DIR.exists():
            raise TeamSACRuntimeUnavailable(f"model package not found: {TEAM_SAC_MODEL_PACKAGE_DIR}")

        try:
            bundle = self._load_bundle()
            from app.team_runtime.inference_service import run_inference_for_day
        except Exception as exc:
            raise TeamSACRuntimeUnavailable(str(exc)) from exc

        try:
            # The regional_virtual_hub scenario rescales station physics. When the caller
            # injects scenario configs into day_data, they take precedence over the bundle's
            # single-charger manifest spec.
            rows = run_inference_for_day(
                day_data=day_data,
                upper_algo=bundle.upper_algo,
                lower_algo=bundle.lower_algo,
                upper_model=bundle.upper_model,
                lower_agents=bundle.lower_agents,
                shield_config=day_data.get("shield_config_override") or getattr(bundle, "shield_config", None),
                station_config=day_data.get("station_config"),
            )
        except Exception as exc:
            raise TeamSACRuntimeUnavailable(f"inference failed: {exc}") from exc

        return TeamSACResult(rows=rows, manifest=bundle.manifest)

    def _load_bundle(self) -> Any:
        if self._bundle is None:
            from app.team_runtime.model_loader import load_model_bundle

            self._bundle = load_model_bundle()
        return self._bundle
