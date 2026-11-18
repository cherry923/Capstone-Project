# Data And Forecast Guide

이 문서는 PV/EV 예측 파트만 설명한다. 의사결정 모델은
[decision_experiments.md](decision_experiments.md)를 보면 된다.

## 실제값과 예측값

실험 CSV에는 실제값과 예측값이 분리되어 있다.

| 컬럼 | 의미 | 쓰는 곳 |
|---|---|---|
| `pv_forecast` | 운영 시점에 알고 있다고 가정하는 PV 예측값 | 의사결정 입력 |
| `demand_forecast` | 운영 시점에 알고 있다고 가정하는 EV 수요 예측값 | 의사결정 입력 |
| `pv_actual` | 실제 발생한 PV 발전량 | 비용 정산, 평가 |
| `demand_actual` | 실제 발생한 EV 충전 수요 | 비용 정산, 평가 |

의사결정 모델은 `forecast` 컬럼을 보고 움직이고, 최종 요금은 `actual`
컬럼으로 다시 계산한다. 이 구분이 무너지면 실험이 미래 실제값을 훔쳐보는
형태가 되므로 꼭 지켜야 한다.

## EV 데이터

현재 메인 의사결정 실험의 EV는 실제 충전 데이터를 자동 군집화한 것이
아니다. KEPCO 충전 데이터를 시설 유형 기준으로 묶은 것이다.

| station | 의미 | 데이터 그룹 |
|---:|---|---|
| 0 | 주거지형 충전소 | `residential` |
| 1 | 상업/도심형 충전소 | `commercial_urban` |
| 2 | 공공시설형 충전소 | `public_facility` |

만드는 과정은 다음과 같다.

1. KEPCO 충전 session 데이터를 시간별 kWh 수요로 바꾼다.
2. 시설 유형별로 합친다.
3. 각 유형을 하나의 대표 station처럼 둔다.
4. station별 하루 총 EV 수요를 비슷한 규모로 정규화한다.
5. 시간대별 모양은 원본 패턴을 유지한다.

최종 프론트/제출 보고서 기준 source:

| 항목 | 경로 |
|---|---|
| KEPCO 시설유형 시간별 수요 | `data/processed/ev/kepco_facility_hourly_20260520/kepco_facility_2020_2022_facility_group_hourly.csv` |
| 최종 비교 train CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_train.csv` |
| 최종 비교 test CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_test.csv` |

제주 EV 전체 수요도 따로 있다. 이 데이터는 실제 제주 충전 이력이라 지역
일관성은 좋지만, 시설 유형 구분이 없어서 현재 3-station 공유 실험에는 바로
쓰지 않았다.

| 항목 | 경로 |
|---|---|
| 제주 EV 원본 | `data/raw/public-data-check-2026-05-03/jeju_ev_charge_history_15109706.csv` |
| 제주 EV 전체 시간별 수요 | `data/processed/ev/hourly/jeju_ev_total_hourly_clean.csv` |
| 제주 EV 상위 50개 station | `data/processed/ev/hourly/jeju_ev_station_hourly_top50.csv` |

## EV 예측 모델

최종 프론트/제출 보고서 결과에 사용한 EV 예측은 Transformer v2 기반이다.
예전 메인 실험에는 rolling 통계 모델 `evfcst_v1`을 썼지만, 현재 표시되는
최종 비교 수치는 EV Transformer v2 peak-aware shape-calibrated p90 CSV를
기준으로 한다.

| 모델 | 방식 | 상태 |
|---|---|---|
| `evtfm_v2_peakaware_shapecal_p90` | 과거 EV 수요 흐름과 목표일 calendar feature를 보는 Transformer v2 + peak-aware 보정 + p90 수요대역 | 최종 프론트/보고서 수치 사용 |
| `evfcst_v1` | 같은 요일, 같은 시간의 과거 4주 평균 | 이전 headline 결과 |
| `evfcst_v3_p90winsor` | 같은 방식이지만 과거 outlier를 90% 분위수로 cap | 개선 후보 |
| `evtfm_v1` | 과거 EV 수요 모양과 목표일 calendar feature를 보는 Transformer shape 모델 | 이전 후보 |

메인 EV v1은 다음처럼 생각하면 된다.

> 다음 금요일 14시 수요를 예측하려면, 과거 금요일 14시 수요 4주치를 평균낸다.

EV v3는 과거 값 중 너무 큰 spike를 줄이기 위해 예측 시점 이전 56일의
station-hour 90% 분위수로 cap한다. 목표일 실제값은 보지 않는다.

EV Transformer 계열은 하루 총량과 하루 안의 시간대별 모양을 나눠서 예측한다.
총량은 과거 같은 요일 수요를 기반으로 추정하고, 시간대별 모양은 작은
Transformer가 과거 수요 흐름과 목표일의 요일/시간 정보를 보고 예측한다.
목표일 실제 수요는 입력으로 쓰지 않는다.

Jan-Feb 기준 EV 성능:

| 모델 | 시간별 WAPE | Bias | RMSE | 판단 |
|---|---:|---:|---:|---|
| `evtfm_v2_peakaware_shapecal_p90` | 8.80% | - | - | 최종 프론트/보고서 수치 사용 |
| `evtfm_v2_peakaware_shapecal_p90` peak-hour | 5.42% | - | - | 피크 시간대 WAPE |
| `evfcst_v1` | 11.78% | -0.03% | 152.48 | 이전 headline 결과 |
| `evfcst_v3_p90winsor` | 9.38% | -2.79% | 59.50 | 예측은 개선, 의사결정 메인 교체는 보류 |
| `evtfm_v1` | 9.77% | -0.03% | 43.57 | Transformer 후보. seed1 의사결정에서는 공유 개선폭이 좋지만 3-seed 검증 전 |
| `evtfm_v1_shapecal` | 8.90% | -0.03% | 40.11 | validation-only station-hour shape calibration 후보 |

Transformer shape calibration은 test 실제값을 보정에 쓰지 않는다. train
마지막 validation 구간에서 station-hour별 반복 오차만 계산하고, 일별 station
총량은 보존한 채 시간대별 모양만 약하게 보정한다.

최종 비교용 EV 수요 시나리오는 `evonly_volume_moderate`다. PV는 그대로 두고
충전소별 EV 수요 volume/shape 차이를 키워, 물리 P2P 공유 효과가 실제로
보이는지 검증한 시나리오다.

## PV 데이터

PV는 제주 PV/기상 데이터를 기반으로 한다.

| 항목 | 경로 |
|---|---|
| PV/날씨 시간별 데이터 | `data/processed/pv/site_actual/pv_actual_2018_2023_hourly.csv` |
| 최종 PV/EV forecast artifact | `ai_module/artifacts/sharing_3arm/forecast_observation/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90.json` |

PV 원천 데이터는 2018-01-01부터 2023-12-31까지 있다. 의사결정 평가는
2022년 1~2월을 쓴다. PV 예측 모델은 더 긴 과거 데이터로 학습하고, 그
예측값을 의사결정 시나리오에 붙이는 구조라서 기간이 다르다.

## PV 예측 모델

현재 프론트/제출 보고서 수치에 채택한 PV 예측은 tree 기반 회귀 모델이다.
AI 서버의 PV prediction endpoint에는 Han TFT 런타임 패키지가 있지만, 최종
비교 수치에는 그 TFT 패키지를 쓰지 않았다.

| 모델 | 설명 | 상태 |
|---|---|---|
| `tree_v5_hgb_absolute_error` | Histogram Gradient Boosting 기반 capacity factor 예측 | 최종 프론트/보고서 수치 사용 |
| `tft_v3` | 긴 과거 구간을 보는 TFT-style 모델 | 오프라인 최종 수치 미채택 |
| `tft24x9_v6` | 24시간 x 9개 feature 구조 | 미채택 |
| `tft24x9_cyclic_v6` | 시간 cyclic feature 추가 | 미채택 |

PV 모델은 kWh를 바로 맞히기보다 capacity factor를 예측한 뒤 station별 PV
규모에 맞게 다시 kWh로 바꾼다.

Jan-Feb 기준 PV 성능:

| 모델 | 시간별 WAPE | 일별 WAPE | Bias | 판단 |
|---|---:|---:|---:|---|
| `tft24x9_v6` | 22.04% | 13.77% | +2.08% | 미채택 |
| `tft24x9_cyclic_v6` | 22.06% | 14.70% | -2.00% | 미채택 |
| `tft_v3` | 20.93% | 16.04% | -8.15% | 미채택 |
| `tree_v5_hgb_absolute_error` | 12.01% | 4.98% | -1.30% | 현재 채택 |

주의할 점:

- tree v5는 현재 수치가 가장 좋다.
- 보고서에는 "PV는 tree 기반 회귀 모델, EV는 Transformer v2 기반 수요
  예측 모델"이라고 적는 것이 현재 프론트 수치와 맞다.
- "PV는 TFT"라고 쓰면 AI 서버 런타임 endpoint 설명으로는 맞을 수 있지만,
  최종 비교 그래프의 수치 근거와는 맞지 않는다.
- 다만 현재 문서화 기준으로는 target-day weather를 forecast proxy처럼 쓴다.
- 아주 엄격한 "전날 밤에 다음날 전체 24시간 예측" 조건으로 말하려면
  safe-lag 재검증이 필요하다.

## 그래프 artifact

발표/공유용 그래프는 여기 있다.

| 그래프 | 경로 |
|---|---|
| 대표 주간 실제/예측 시계열 | `ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_actual_timeseries_representative_week_2022.png` |
| Jan 10-16 실제/예측 시계열 | `ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_actual_timeseries_jan10_16_2022.png` |
| 예측/실제 scatter | `ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_actual_scatter_jan_feb_2022.png` |
| 평균 24시간 profile | `ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_average_24h_profile_jan_feb_2022.png` |
| station별 WAPE | `ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_wape_by_station_jan_feb_2022.png` |

지표 원본:

```text
ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_metrics_jan_feb_2022.json
```
