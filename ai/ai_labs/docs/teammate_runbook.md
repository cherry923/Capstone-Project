# Teammate Runbook

팀원이 바로 할 수 있는 작업을 난이도별로 나눴다.

## 0. 준비

프로젝트 전체 checkout 기준으로 실행한다.

```bash
cd <workspace-root>
```

AI API 서버만 실행할 때는 `ai/` 안에서 가상환경을 쓴다.

```bash
cd ai
/opt/homebrew/bin/python3.13 -m venv .venv313
. .venv313/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

실험 artifact 확인은 프로젝트 루트에서 한다.

```bash
python3 ai/ai_labs/scripts/check_experiment_artifacts.py
```

## 1. 결과표만 확인하기

가장 쉬운 경로다. 학습을 돌리지 않는다.

```bash
python3 ai/ai_labs/scripts/check_experiment_artifacts.py
```

확인할 핵심 파일:

```text
ai_module/artifacts/sharing_3arm/forecast_observation/defaults_and_milp_comparison_2026-05-28.json
ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_metrics_jan_feb_2022.json
```

이 단계에서 팀원이 확인할 수 있는 것:

- PV/EV 예측 WAPE.
- 6개 운영 방식 total@8320 비교.
- grid-only/passive-PV/local no-P2P 대비 절감률.
- peak violation과 share/day.

## 2. 그래프 확인하기

그래프 파일은 이미 생성되어 있다.

```text
ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/
```

주로 보면 되는 그림:

```text
pv_ev_forecast_actual_timeseries_representative_week_2022.png
pv_ev_forecast_actual_timeseries_jan10_16_2022.png
pv_ev_forecast_actual_scatter_jan_feb_2022.png
pv_ev_forecast_average_24h_profile_jan_feb_2022.png
pv_ev_forecast_wape_by_station_jan_feb_2022.png
```

## 3. AI API 서버 smoke test

이건 실험 재현이 아니라 서버 응답 확인이다.

```bash
cd ai
. .venv313/bin/activate
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/api/v1/ai/flow/dispatch-24h \
  -H "Content-Type: application/json" \
  -d '{"request_id":"team-smoke","target_date":"2026-05-07","init_soc":[0.55,0.5,0.45]}'
```

성공 기준:

- `code`가 `SUCCESS`.
- 24시간 x 3 station = command 72개.
- EV payload가 historical scenario라는 warning이 표시된다.

주의:

- 이 API smoke test는 메인 논문식 성능표를 다시 계산하는 테스트가 아니다.
- 성능표는 `ai_module`의 오프라인 실험 artifact 기준이다.

## 4. 예측 모델 실험 다시 돌리기

가벼운 편이지만 그래도 시간이 걸릴 수 있다.

EV hourly dataset 재생성:

```bash
ai_module/.venv/bin/python ai_module/scripts/build_ev_hourly_dataset.py --station-top-n 50
```

EV 기본 비교:

```bash
ai_module/.venv/bin/python ai_module/scripts/run_ev_total_shape_24h_experiment.py \
  --output-stem ev_total_shape_24h_model_comparison
```

PV Transformer/TFT 계열은 문서화된 command가 `ai_module/README.md`에 있다.
현재 프론트/제출 보고서 성능표는 PV `tree_v5_hgb_absolute_error`와
EV Transformer v2 p90 artifact를 기준으로 한다. `ai` 서버의 Han TFT PV
패키지는 API 런타임 경로이고, 최종 비교 그래프의 PV 모델은 아니다.

## 5. 의사결정 평가만 다시 돌리기

학습된 lower/upper artifact가 이미 있으면 평가만 다시 돌릴 수 있다.
다만 경로가 길어서 팀원이 바로 치기보다는 기존 JSON을 확인하는 편이 안전하다.

관련 스크립트:

```text
ai_module/scripts/paper_repro/eval_contract_guarded_sharing.py
ai_module/scripts/paper_repro/compare_five_methods_asym525.py
```

입력 artifact:

```text
ai_module/artifacts/sharing_3arm/multi_noshare_.../lower_PI_SAC_FULL_{0,1,2}.pt
ai_module/artifacts/sharing_3arm/shared_pisac_.../upper_SHARED_FULL.pt
data/processed/ev/sharing_3arm/*_train.csv
data/processed/ev/sharing_3arm/*_test.csv
```

## 6. 전체 재학습

처음부터 전체 재학습은 무겁다. 보통 다음 순서다.

1. scenario CSV 준비.
2. station 0/1/2 lower PI-SAC 각각 300k step 학습.
3. shared upper PI-SAC 15k step 학습.
4. corrected tariff evaluation.
5. five-method comparison.

이 단계는 tmux, 긴 실행 시간, artifact 경로 관리가 필요하다. 팀원이 실험을
확장해야 할 때만 진행한다.

## 7. 추천 역할 분담

| 역할 | 맡기기 좋은 작업 |
|---|---|
| 발표/문서 담당 | `ai_labs/docs` 문서와 report asset 그림 확인 |
| 서버 담당 | `ai/docs/TEAM_AI_SERVER_RUNBOOK.md` 기준 API smoke test |
| 예측 담당 | PV/EV forecast artifact와 WAPE 재계산 |
| 의사결정 담당 | `defaults_and_milp_comparison_2026-05-28.json` 해석, 필요 시 평가 재실행 |

처음에는 전체 재학습보다 artifact 확인과 표 재생성을 먼저 시키는 게 좋다.
