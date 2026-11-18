from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app.services.decision import LowerDecisionService, MultiStationDecisionService, UpperDecisionService
from app.services.ev_forecast import EVDemandForecastService
from app.services.flow import DispatchFlowService
from app.services.pv_prediction import PVPredictionService


app = FastAPI(title="Multi-EV Charging AI Server", version="0.1.0")

pv_service = PVPredictionService()
ev_service = EVDemandForecastService()
upper_service = UpperDecisionService()
lower_service = LowerDecisionService()
multi_station_service = MultiStationDecisionService()
dispatch_flow_service = DispatchFlowService()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/ai/predictions/pv")
def predict_pv(payload: dict[str, Any]) -> dict[str, Any]:
    return pv_service.predict(payload)


@app.post("/api/v1/ai/predictions/ev")
def predict_ev(payload: dict[str, Any]) -> dict[str, Any]:
    return ev_service.predict(payload)


@app.post("/api/v1/ai/decisions/share-plan")
def share_plan(payload: dict[str, Any]) -> dict[str, Any]:
    return upper_service.generate_share_plan(payload)


@app.post("/api/v1/ai/decisions/local-policy")
def local_policy(payload: dict[str, Any]) -> dict[str, Any]:
    return lower_service.generate_local_policy(payload)


@app.post("/api/v1/ai/decisions/multi-station")
def multi_station_policy(payload: dict[str, Any]) -> dict[str, Any]:
    """Convenience API that chains share-plan and local-policy.

    The project documents keep share-plan and local-policy as separate contract
    endpoints. This wrapper is only for whole-network demos and backend
    integration smoke tests.
    """

    return multi_station_service.generate(payload)


@app.post("/api/v1/ai/flow/dispatch-24h")
def dispatch_24h(payload: dict[str, Any]) -> dict[str, Any]:
    """Full AI demo flow: PV/EV forecasts -> upper decision -> lower commands."""

    return dispatch_flow_service.generate_dispatch_24h(payload)
