# 팀 실행 가이드: AI 서버

이 문서는 팀원이 `sejong-capstone-team7/ai` 레포만 clone해도 최종 발표용 24시간 dispatch API를 실행할 수 있게 만든 기준이다.

## 현재 레포에 포함된 모델 기준

- PV 예측 API 런타임: `models/han_tft_pv_incheon_20250506`
- EV 수요 예측 입력 payload: `app/data/ev_hybrid_calendar_24h_blend_sac_payload.json`
- 상위/하위 의사결정 (production default): `models/evcs_api_model_v4_share_milp_shield`
  (SoftPeakSlackMILP 상위 공유 planner + DefaultLowerAgent + forecast-aware C6 safety shield. `model_status=TEAM_SHARE_MILP_SHIELD_LOADED`로 응답에 표기됨)
  - `evcs_api_model_v3_fallback_shield`는 no-share safety fallback 패키지로 남아 있다.
  - `evcs_api_model_v1_synthetic_MILP_PI_SAC_FULL`는 synthetic 학습 모델로 multi-station에서 OOD/불안정이라 **research/ablation 전용으로 강등**됨 (production default 아님). 쓰려면 `TEAM_SAC_MODEL_PACKAGE_DIR` 환경변수로 명시 지정.

### 최종 보고서/프론트 수치 기준

위 `models/han_tft_pv_incheon_20250506`은 AI 서버의 PV 예측 API 런타임
패키지다. 제출 보고서와 프론트의 "Decision Model Comparison" 그래프에
나오는 최종 비교 수치는 이 API를 실시간 호출해서 만든 값이 아니다.

최종 비교 수치의 예측모델 기준은 다음과 같다.

| 항목 | 최종 비교 수치 기준 |
|---|---|
| PV 예측 | tree 기반 회귀 모델 `tree_v5_hgb_absolute_error` |
| EV 예측 | EV Transformer v2 peak-aware shape-calibrated p90 |
| 비교 시나리오 CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_test.csv` |
| 최종 5-method 결과 | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42_physical_oracle.json` |

따라서 보고서에는 "PV는 TFT"라고 쓰지 않는다. 정확한 표현은
"PV는 tree 기반 회귀 예측 모델, EV는 Transformer v2 기반 수요 예측 모델"이다.

예전에는 EV payload 기본 경로가 로컬 `../ai_module/artifacts/...`였다. `ai_module`은 별도 git 레포가 아니므로 팀원이 clean clone하면 파일을 찾지 못한다. 이제 기본 경로는 `ai/app/data/...`이고, 필요하면 `EV_SAC_PAYLOAD_PATH` 환경변수로 다른 payload를 지정할 수 있다.

## 로컬 실행

```bash
cd /path/to/ai
/opt/homebrew/bin/python3.13 -m venv .venv313
. .venv313/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

다른 터미널에서 확인한다.

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/api/v1/ai/flow/dispatch-24h \
  -H "Content-Type: application/json" \
  -d '{"request_id":"team-smoke","target_date":"2026-05-07","init_soc":[0.55,0.5,0.45]}'
```

성공 기준:

- `code`가 `SUCCESS`
- `data.dispatch.summary.command_count`가 `72`
- `data.model_status`가 팀 모델 로드 또는 fallback 상태를 명시
- `data.warnings`에 `historical payload` 경고가 한 줄 포함된다 (정상)
- `data.forecasts.source.ev_detail.historical_scenario`가 `true`로 표시된다 (정상)

### EV payload는 historical scenario이다

`app/data/ev_hybrid_calendar_24h_blend_sac_payload.json`은 `base_datetime = 2022-06-23 00:00:00` 기준의 고정 historical payload이다. dispatch API에 `target_date=2026-05-07` 같은 미래 날짜를 넣어도 EV 수요 값은 그 날짜에 대한 live forecast가 아니라 historical scenario가 그대로 나온다. 응답의 `data.warnings`와 `data.forecasts.source.ev_detail.target_date_mismatch_days`로 이 사실이 명시된다.

운영 적용 전에 historical payload가 dispatch에 새는 것을 막고 싶으면 `EV_STRICT_TARGET_DATE=1` (+ 옵션 `EV_STRICT_MISMATCH_DAYS=365`) 환경 변수를 켠다. 이 경우 mismatch가 365일을 넘으면 `INVALID_INPUT_VALUE`로 dispatch가 거부된다. 기본은 strict OFF.

## Docker 실행

```bash
cd /path/to/ai
docker build -t capstone-ai .
docker run --rm -p 8000:8000 capstone-ai
```

Docker 이미지는 레포 내부 모델과 payload를 그대로 복사한다. 더 큰 외부 payload를 쓰려면 컨테이너 실행 시 volume mount와 `EV_SAC_PAYLOAD_PATH`를 같이 넘긴다.

```bash
docker run --rm -p 8000:8000 \
  -v /absolute/path/payloads:/payloads:ro \
  -e EV_SAC_PAYLOAD_PATH=/payloads/custom_ev_payload.json \
  capstone-ai
```

## 테스트

```bash
cd /path/to/ai
. .venv313/bin/activate
PYTHONPATH=. python -m unittest discover -s tests
```

테스트가 통과하면 PV/EV 예측 API, 상위/하위 의사결정 API, 24시간 dispatch 응답 shape가 최소 기준을 만족한다.
