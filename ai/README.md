# Multi-EV Charging AI Server

Python REST API server for the capstone AI module.

This repository was created for `sejong-capstone-team7/ai`. It keeps the project
documents as the contract:

- `POST /api/v1/ai/predictions/pv`
- `POST /api/v1/ai/predictions/ev`
- `POST /api/v1/ai/decisions/share-plan`
- `POST /api/v1/ai/decisions/local-policy`
- `POST /api/v1/ai/decisions/multi-station`
- `POST /api/v1/ai/flow/dispatch-24h`

`multi-station` is a current-hour demo wrapper that chains the documented
`share-plan` and `local-policy` APIs. `flow/dispatch-24h` is the full demo path:
PV forecast, EV forecast, upper sharing decision, lower local policy, and
station command response for 24 hours.

## Current model wiring

- PV: loads Han Mingu's packaged TFT-style PV model from
  `models/han_tft_pv_incheon_20250506` when PyTorch is available. The package
  contains `best_model.pt`, `scalers.json`, `manifest.json`, metrics, and the
  validation predictions. If the runtime is missing or the package is absent,
  the endpoint falls back to the previous API-compatible shadow predictor.
- EV: uses the current EV SAC/share-plan payload artifact:
  `app/data/ev_hybrid_calendar_24h_blend_sac_payload.json`.
- Upper/lower decision: `flow/dispatch-24h` loads the production default
  `evcs_api_model_v4_share_milp_shield` package when the PyTorch/SB3/PuLP
  dependencies are installed. It uses a stateless SoftPeakSlackMILP upper
  planner for visible inter-station sharing and DefaultLowerAgent actions
  wrapped by the forecast-aware C6 safety shield (peak relief + SoC projection),
  reported as `model_status=TEAM_SHARE_MILP_SHIELD_LOADED`. The previous
  `evcs_api_model_v3_fallback_shield` package remains a no-share safety fallback.
  The synthetic `evcs_api_model_v1_synthetic_MILP_PI_SAC_FULL` package (MILP
  upper + 3 PI-SAC lower agents) is OOD/unstable on the multi-station aggregate
  and is kept for research/ablation only (set `TEAM_SAC_MODEL_PACKAGE_DIR` to use
  it). If the heavy runtime is unavailable, the endpoint falls back to the
  rule-shaped API path and reports that status in the response.

## Final report / frontend comparison source

The runtime API wiring above is not the source of the final decision-comparison
numbers shown in the frontend. Those numbers are static offline experiment
results generated under `../ai_module` and exported to the server frontend.

For the final report and the frontend "Decision Model Comparison" graph, use
this source of truth:

| part | final comparison source |
|---|---|
| PV forecast | tree-based regression `tree_v5_hgb_absolute_error` |
| EV forecast | EV Transformer v2 peak-aware shape-calibrated p90 forecast |
| scenario CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_test.csv` |
| 5-method result | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42_physical_oracle.json` |
| frontend asset | `server/frontend/public/assets/operation-comparison/evonly_vmoderate_v2p90_pvess_multiseed.json` |

Important distinction:

- `POST /api/v1/ai/predictions/pv` can use Han's TFT PV package at runtime.
- The final report/frontend comparison does **not** use that TFT package for PV.
  It uses the offline tree v5 PV forecast above.

## Run

```bash
/opt/homebrew/bin/python3.13 -m venv .venv313
. .venv313/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Test

```bash
PYTHONPATH=. python -m unittest discover -s tests
```

## 24h dispatch smoke request

```bash
curl -X POST http://localhost:8000/api/v1/ai/flow/dispatch-24h \
  -H "Content-Type: application/json" \
  -d '{"request_id":"demo-dispatch","target_date":"2026-05-07","init_soc":[0.55,0.5,0.45]}'
```

The response contains 72 station commands: 24 hours times 3 stations. Each
command includes `share_energy_kwh`, `ess_action`, `pv_priority`, SoC before and
after, grid cost, and a compact command label.

## Team runbook

For clean-clone setup, smoke checks, Docker execution, and server integration,
see `docs/TEAM_AI_SERVER_RUNBOOK.md`.

## Offline experiment lab

The headline forecast/decision results are produced by offline CSV-based
experiments in `../ai_module`, not by the FastAPI server itself. Team-facing
guides for those experiments live under `ai_labs/`.

Start here:

- `ai_labs/README.md`
- `ai_labs/docs/data_and_forecasts.md`
- `ai_labs/docs/decision_experiments.md`
- `ai_labs/docs/result_history.md`
- `ai_labs/docs/teammate_runbook.md`

Quick artifact check from the workspace root:

```bash
python3 ai/ai_labs/scripts/check_experiment_artifacts.py
```

## Rebuild Han PV package

```bash
PYTHONPATH=. python scripts/train_han_pv_model.py \
  --pv-csv "../artifacts/received_models/2026-05-06/han_pv_data/한국전력거래소_지역별 시간별 태양광 및 풍력 발전량_20251231 (1) (2).csv" \
  --weather-csv "../artifacts/received_models/2026-05-06/han_pv_data/OBS_ASOS_TIM_20260429140801 (1).csv" \
  --output-dir models/han_tft_pv_incheon_20250506 \
  --epochs 30
```

## Design references

- `../docs/testing_ai.md`
- `../docs/시험_절차서_AI모듈_v5.md`
- `../docs_local/translated_notes/ai_usecase_flows_hierarchical.md`
- `../docs_local/translated_notes/SAC_논문_한글번역_요약_2026-03-16.md`
- `../docs_local/translated_notes/PI-SAC_논문_한글번역_상세_2026-03-18.md`
- `../artifacts/kakaotalk_capstone_ai_analysis/analysis_report.md`
