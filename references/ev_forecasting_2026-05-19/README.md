# EV Forecasting Literature Pack (2026-05-19)

## 목적

EV 수요 예측 모델 개선 방향, 평가 지표, 그리고 현재 프로젝트의 WAPE 산정 방식이 타당한지 검증하기 위해 공개 접근 가능한 논문 PDF를 모았다.

기존 내부 조사 파일:

- `ai_module/artifacts/ev_model_root_cause_literature_review_20260517.md`
- `ai_module/artifacts/ev_full_investigation_report_2026-05-19.md`

오늘 확인 결과 `docs` 레포 안에는 EV 수요예측 논문 PDF 묶음이 따로 없었다. 기존 `docs/references`에는 PI-SAC/강화학습 관련 PDF는 있었지만 EV forecasting 지표 검증용 논문 묶음은 없어서 이 폴더를 새로 만들었다.

## 내려받은 논문 PDF

| 파일 | 주제 | 원문 |
|---|---|---|
| `papers/2019_zhu_ev_charging_load_forecasting_deep_learning_energies.pdf` | EV 충전 부하 예측 딥러닝 비교 | https://www.mdpi.com/1996-1073/12/14/2692 |
| `papers/2021_huttel_deep_spatiotemporal_ev_charging_arxiv2106_10940.pdf` | T-GCN 기반 시공간 EV 충전 수요 예측 | https://arxiv.org/abs/2106.10940 |
| `papers/2022_li_probabilistic_charging_power_rl_arxiv2204_07905.pdf` | RL-assisted probabilistic EVCS charging power forecast | https://arxiv.org/abs/2204.07905 |
| `papers/2023_xue_ast_gin_station_availability_sensors.pdf` | AST-GIN 충전소 availability 예측 | https://www.mdpi.com/1424-8220/23/4/1975 |
| `papers/2024_ali_location_probabilistic_mq_tcn_arxiv2409_11862.pdf` | location-based MQ-TCN 확률 부하 예측 | https://arxiv.org/abs/2409.11862 |
| `papers/2024_gunasekaran_egru_rkoa_gcn_discover_applied_sciences.pdf` | EGRU + graph convolution demand prediction | https://link.springer.com/article/10.1007/s42452-024-06326-x |
| `papers/2024_wstgcn_ev_charging_load_prediction_energies.pdf` | weight-fusion STGCN EV charging load prediction | https://www.mdpi.com/1996-1073/17/19/4798 |
| `papers/2024_zheng_coherent_hierarchical_probabilistic_arxiv2411_00337.pdf` | coherent hierarchical probabilistic EV demand forecast | https://arxiv.org/abs/2411.00337 |
| `papers/2025_hussain_cat_former_scientific_reports.pdf` | CAT-Former short-term EV charging demand forecast | https://www.nature.com/articles/s41598-025-20557-x |
| `papers/2025_urbanev_open_benchmark_scientific_data.pdf` | UrbanEV benchmark dataset | https://www.nature.com/articles/s41597-025-04874-4 |
| `papers/2026_evformer_citywide_ev_charging_load_forecasting.pdf` | EVformer citywide charging load forecasting | https://www.mdpi.com/2032-6653/17/2/71 |

함께 참고했지만 PDF를 직접 받지 않은 publisher page:

- Buzna et al., hierarchical probabilistic EV load forecasting, Applied Energy 2021: https://www.sciencedirect.com/science/article/pii/S0306261920317207
- Wang et al., heterogeneous spatio-temporal GCN, Transportation Research Part C 2023: https://research.polyu.edu.hk/en/publications/predicting-electric-vehicle-charging-demand-using-a-heterogeneous/
- Wang et al., adaptive spatio-temporal graph recurrent network, Applied Energy 2025: https://www.sciencedirect.com/science/article/pii/S0306261925000509

## 지표 확인 결과

`pdftotext`로 텍스트를 추출한 뒤 `WAPE`, `MAPE`, `RMSE`, `MAE`, `sMAPE`, `NRMSE`, `NMAE`, `PICP`, `Pinball`, `CRPS`를 검색했다.

핵심 결과:

- 다운로드한 EV 논문 11편에서 `WAPE` 직접 사용은 0건이었다.
- EV charging forecasting 논문에서 가장 자주 쓰는 point forecast 지표는 `MAE`, `RMSE`, `MAPE`다.
- `UrbanEV`는 `RMSE`, `MAPE`, `RAE`, `MAE`를 쓴다.
- `CAT-Former`는 `MSE`, `MAE` 중심이고, 관련 연구 표에서는 `RMSE`, `MAPE`, `NMAE`, `NRMSE`도 언급한다.
- 확률예측 논문은 `PICP`, `Pinball`, `CRPS`, coverage 류 지표를 쓴다.
- 일부 EV 논문은 수요가 0 또는 매우 작은 구간에서 `MAPE`가 불안정하므로 `MAPE`를 평가에서 제외하고 `RMSE`, `MAE`, `R2`를 쓴다.

따라서 발표/보고서에서는 WAPE 하나만 쓰면 학술 비교성이 약하다. 현재 프로젝트처럼 24시간 aggregate load 예측에서는 WAPE가 운영적으로 유용하지만, 논문 기준과 맞추려면 다음을 같이 병기하는 것이 안전하다.

- `WAPE`: aggregate 운영 지표. 큰 수요 시간대에 더 큰 가중치를 주므로 ESS/grid 운영 관점에 맞다.
- `MAE`: kWh 단위 절대 오차. 실제 수요 부족/과잉 규모를 설명하기 좋다.
- `RMSE`: 큰 오차에 민감. 피크 시간대 실패를 강조하기 좋다.
- `MAPE`: 논문 비교용. 단, 0 또는 저수요 시간대에서는 왜곡될 수 있으므로 daylight/positive-demand subset과 같이 제시한다.
- `sMAPE`: MAPE 보완용.
- `P10/P50/P90 coverage`, `PICP`, `Pinball`: 확률예측/시나리오 예측을 주장할 때 필요하다.

## 우리 WAPE 산정 방식 검토

현재 helper:

```python
def wape(y_true, y_pred) -> float:
    denom = float(np.sum(np.abs(y_true)))
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)
```

이 방식은 `Σ|actual - pred| / Σ|actual| × 100`이다. 산정 방식 자체는 맞다. 특히 전체 24시간 총 수요, daylight subset, group aggregate처럼 denominator가 충분히 큰 경우에는 MAPE보다 안정적이다.

주의할 점:

- 이 값은 `MAE / mean(|actual|) × 100`과 수학적으로 거의 같다. 즉 NMAE(mean)로도 설명할 수 있다.
- 논문 비교에는 WAPE보다 MAE/RMSE/MAPE가 더 통용된다.
- 새벽처럼 실제 수요가 작고 변동성이 큰 구간은 WAPE도 높게 튄다. 그래서 `24h 전체`, `daylight 7~21시`, `peak 15~18시`, `daily total`을 분리해서 보여줘야 한다.
- `WAPE 평균`과 `전체 합산 WAPE`는 다를 수 있다. 최종 보고서에서는 어떤 aggregation인지 명시해야 한다.

## 우리 방향에 대한 판단

현재 Claude/Codex가 잡은 방향은 논문 흐름과 대체로 맞다.

맞는 부분:

- 데이터 품질 cutoff를 먼저 잡은 것: 논문들은 historical usage가 매우 중요하다고 보며, EV 충전 데이터는 운영상태/누락/설치시점에 민감하다.
- clean historical validation으로 성능을 다시 산정한 것: leakage-free walk-forward 검증은 타당하다.
- WAPE만 보지 않고 MAE/RMSE/MAPE/sMAPE와 coverage를 병기하려는 것: 논문 지표와 맞는다.
- P10/P50/P90 payload와 coverage를 유지하는 것: 확률예측 논문 흐름과 맞는다.
- hard 3그룹 모델보다 station-level/global/hierarchical 구조를 후속으로 보는 것: hierarchical/spatio-temporal 논문 흐름과 맞는다.
- weather/외부변수를 무조건 넣지 않고 ablation으로 검증한 것: UrbanEV factorial 결과처럼 단일 외부변수는 도움을 안 주거나 악화될 수 있다.

조심할 부분:

- “WAPE 9%대”만으로 논문 수준 SOTA라고 말하면 안 된다. 우리 결과는 `Jeju aggregate`이고, 많은 논문은 station/node-level 또는 occupancy/volume 예측이다.
- `target_date=2026-05-07` 결과는 live forecast가 아니라 historical scenario payload다. 발표에서는 clean historical validation 성능과 integration demo를 분리해야 한다.
- 3그룹(거주/비거주/상업지)은 발표 설명에는 좋지만, 모델 hard split 기준으로는 데이터가 줄고 그룹 내부 이질성이 커질 수 있다. 논문 흐름상 group은 feature 또는 hierarchy로 쓰는 편이 더 안전하다.
- EV forecast WAPE 개선이 dispatch cost 개선으로 바로 이어진다고 주장하면 안 된다. 현재 의사결정 구조에서는 forecast accuracy보다 payload bias 제거, scenario safety, demand uncertainty가 더 직접적인 운영 가치다.

## 최종 발표용 문구

```text
EV 수요 예측 평가는 WAPE만으로 보지 않고, EV forecasting 논문에서 일반적으로 쓰는
MAE, RMSE, MAPE, sMAPE를 함께 산정했다. WAPE는 전체 수요 대비 절대오차 비율로,
수요가 큰 시간대의 운영 영향을 더 잘 반영하기 때문에 ESS/grid 의사결정용 aggregate
지표로 유지했다. 다만 논문 비교를 위해 MAPE/RMSE/MAE도 병기한다.

또한 EV 충전 데이터는 충전소별 운영상태, 설치시점, 누락 데이터에 민감하므로,
원본 데이터의 공급 cutoff를 탐지하고 clean historical dataset으로 재학습했다.
그 결과 24시간 전체 WAPE는 10.22%에서 9.36%로, daylight WAPE는 9.44%에서
8.55%로 개선되었다. 이 성능은 2022년 제주 clean historical validation 기준이며,
2026년 실시간 예측 성능을 주장하는 것은 아니다.
```

