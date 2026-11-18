# AI Lab Result Map

이 폴더는 결과 파일을 직접 복사해서 쌓는 곳이 아니다. 현재 결과는
`ai_module/artifacts`에 있고, 여기서는 팀원이 어떤 결과를 봐야 하는지
정리한다.

## Main Result

| 구분 | 경로 |
|---|---|
| 양쪽 default + MILP 비교 JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/defaults_and_milp_comparison_2026-05-28.json` |
| 중간 결과 breakdown JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/midterm_defensible_result_breakdown_2026-05-28.json` |
| 5-method source JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_fcstpeakrisk_mtarget_strongpeak_multiseed_tariff8320_seed1_2_42_forecast_rolling_d110_physical_both_oracles.json` |
| EV Transformer 후보 5-method JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_fcstpeakrisk_mref090_strongpeak_tariff8320_seed1_aligned_oracle.json` |
| EV Transformer shape-cal 민감도 JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_shapecal_existingpolicy_tariff8320_seed1_aligned_oracle.json` |
| EV Transformer shape-cal full retrain JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_shapecal_fullretrain_tariff8320_seed1_aligned_oracle.json` |
| EV Transformer shape-cal 3-seed JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_shapecal_multiseed_tariff8320_seed1_2_42_aligned_oracle.json` |
| EV Transformer shape-cal lookahead 3-seed JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_shapecal_fcstlookahead_multiseed_tariff8320_seed1_2_42_aligned_oracle.json` |
| EV Transformer mixed share-aware 3-seed JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_shapecal_fcstlookahead_shareaware_mixsoftzero035_multiseed_tariff8320_seed1_2_42_aligned_oracle.json` |
| EV Transformer v2 p90 peakrisk seed1 JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_peakqueuefcst_seed1_tariff8320_physical_oracle.json` |
| EV Transformer v2 p90 share-aware fine-tune zero-sum sanity JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_shareawareft_seed1_tariff8320_physical_oracle.json` |
| EV Transformer v2 p90 share-aware fine-tune pv_ess sanity JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_shareawareft_pvess_seed1_tariff8320_physical_oracle.json` |
| EV Transformer v2 p90 share-aware fine-tune pv_only sanity JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_shareawareft_pvonly_seed1_tariff8320_physical_oracle.json` |
| Main physical P2P pv_ess 3-seed JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_fcstpeakrisk_pvess_mtarget_multiseed_tariff8320_seed1_2_42_physical_oracle.json` |
| Main physical P2P pv_only 3-seed JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_fcstpeakrisk_pvonly_mtarget_multiseed_tariff8320_seed1_2_42_physical_oracle.json` |
| EV-only volume-moderate physical P2P 3-seed JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42_physical_oracle.json` |

## Forecast Figures

| 구분 | 경로 |
|---|---|
| 대표 주간 실제/예측 시계열 | `ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_actual_timeseries_representative_week_2022.png` |
| Jan 10-16 실제/예측 시계열 | `ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_actual_timeseries_jan10_16_2022.png` |
| 예측/실제 scatter | `ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_actual_scatter_jan_feb_2022.png` |
| 평균 24시간 profile | `ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_average_24h_profile_jan_feb_2022.png` |
| station별 WAPE | `ai_module/artifacts/report_assets/forecast_model_figures_2026-05-28/pv_ev_forecast_wape_by_station_jan_feb_2022.png` |

## Frontend / Report Final Numbers

이 표가 현재 프론트의 "Decision Model Comparison" 그래프와 제출 보고서에
맞춰 써야 하는 최종 수치다. PV는 `tree_v5_hgb_absolute_error`, EV는
Transformer v2 peak-aware shape-calibrated p90, 상위 공유 projection은
physical `pv_ess` 조건이다.

| method | total@8320 M KRW | grid-only 대비 | passive-PV 대비 | local no-P2P 대비 | share/day |
|---|---:|---:|---:|---:|---:|
| Grid-only/no-PV | 198.663 | +0.00% | +51.27% | +70.50% | 0 |
| Passive-PV default | 131.333 | -33.89% | +0.00% | +12.71% | 0 |
| Local ESS SAC (no P2P) | 116.520 | -41.35% | -11.28% | +0.00% | 0 |
| Forecast-based Shared PI-SAC | 110.703 | -44.28% | -15.71% | -4.99% | 977 |
| Hindsight MILP upper bound | 95.559 | -51.90% | -27.24% | -17.99% | 1720 |

보고서에서 4개 모델만 보여줄 때는 `Passive-PV default`, `Local ESS SAC`,
`Forecast-based Shared PI-SAC`, `Hindsight MILP upper bound`를 사용한다.
Grid-only 수치는 PV 사용 효과까지 포함한 참고 기준으로 함께 적는다.

## Legacy Accepted Zero-Sum Headline (Reference Only)

이 표는 기존 headline 결과다. 상위 공유 제약은 `zero_sum`이라 충전소 간
순공유량 합은 맞추지만, PV/ESS 잉여 기반 export 제약을 직접 강제하지 않는다.
물리 P2P 주장이나 최종 프론트 그래프에는 위 final numbers를 사용한다.

| method | total@8320 M KRW | grid-only 대비 | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|---:|
| Grid-only default | 188.732 | +0.00% | +33.67% | +47.29% |
| Passive-PV default | 141.192 | -25.19% | +0.00% | +10.19% |
| Local ESS SAC (no P2P) | 128.136 | -32.11% | -9.25% | +0.00% |
| Forecast-based Shared PI-SAC | 117.369 | -37.81% | -16.87% | -8.40% |
| Forecast rolling MILP | 122.100 | -35.31% | -13.52% | -4.71% |
| Hindsight MILP upper bound | 105.356 | -44.18% | -25.38% | -17.78% |

## Main Physical P2P Sanity Check

이 표는 같은 PV tree v5 + EV v1 + seed1/2/42 조건에서 상위 공유 projection만
물리 제약으로 바꾼 결과다.

| setting | Shared PI-SAC total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 | share/day |
|---|---:|---:|---:|---:|
| original `zero_sum` | 117.369 | -16.87% | -8.40% | 3773 |
| `pv_ess` | 125.547 | -11.08% | -2.02% | 427 |
| `pv_only` | 127.447 | -9.73% | -0.54% | 121 |

읽는 법:

- `zero_sum` 결과는 공유량이 하루 `3773 kWh`로 커서 물리 P2P 성능으로 주장하기 어렵다.
- PV 잉여와 ESS 여유 export를 허용하는 `pv_ess`에서는 local 대비 개선폭이 `-2.02%`다.
- 동시간 PV 잉여만 허용하는 `pv_only`에서는 local 대비 개선폭이 `-0.54%`다.
- 따라서 물리 P2P 기준의 방어 가능한 메인 공유 효과는 `pv_ess` 기준 `-2.02%`로 보는 것이 안전하다.

## EV-Only Demand Asymmetry Physical P2P 3-Seed

이 표는 PV는 그대로 두고 EV 수요만 충전소별로 재배치한
`evonly_volume_moderate` 민감도 시나리오다. 목적은 실제 P2P 공유가
나오려면 어떤 수요 비대칭이 필요한지 확인하는 것이다. 상위 공유 projection은
`pv_ess`라서 PV 잉여와 ESS 여유 export만 허용한다.

`grid-only` 대비 절감률은 PV 도입 효과까지 포함한다. 발표/논문 비교에서는
`passive-PV default` 대비와 `local no-P2P` 대비를 주 절감률로 사용한다.

| method | total@8320 M KRW | grid-only 대비 | passive-PV 대비 | local no-P2P 대비 | share/day |
|---|---:|---:|---:|---:|---:|
| Grid-only/no-PV | 198.663 | +0.00% | +51.27% | +70.50% | 0 |
| Passive-PV default | 131.333 | -33.89% | +0.00% | +12.71% | 0 |
| Local ESS SAC (no P2P) | 116.520 | -41.35% | -11.28% | +0.00% | 0 |
| Soft-MILP P2P + local SAC | 115.053 | -42.09% | -12.40% | -1.26% | 553 |
| Forecast-based Shared PI-SAC | 110.703 | -44.28% | -15.71% | -4.99% | 977 |
| Forecast rolling MILP | 111.958 | -43.64% | -14.75% | -3.92% | 1378 |
| Hindsight MILP upper bound | 95.559 | -51.90% | -27.24% | -17.99% | 1720 |

읽는 법:

- 같은 physical `pv_ess` 제약에서도 수요 비대칭이 커지면 공유 효과가 local 대비 `-4.99%`까지 커진다.
- Forecast-based Shared PI-SAC `110.703M`은 Forecast rolling MILP `111.958M`보다 낮다.
- `grid-only` 대비 Shared PI-SAC `-44.28%`는 PV 효과와 EV 수요 재배치 효과가 함께 들어간 값이므로 교수님 PI-SAC 논문 수치와 직접 비교하지 않는다.
- 이 결과는 "물리 P2P가 의미 있으려면 충전소별 EV 수요 shape/volume 차이가 필요하다"는 시나리오 근거다.
- 기존 main 데이터의 headline을 대체하는 값은 아니며, EV-only 민감도 결과로 분리해서 써야 한다.

## EV Transformer Candidate

이 표는 seed1 단일 후보 검증이다. 메인 3-seed 결과를 대체하지 않는다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +3.85% |
| Local ESS SAC (no P2P) | 135.955 | -3.71% | +0.00% |
| Soft-MILP P2P + local SAC | 133.299 | -5.59% | -1.95% |
| Forecast-based Shared PI-SAC | 116.396 | -17.56% | -14.39% |
| Forecast rolling MILP | 97.493 | -30.95% | -28.29% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -44.45% |

## EV Transformer Shape Calibration Sensitivity

이 표는 `evtfm_v1` 기존 정책에 validation-only shape-calibrated test CSV를
끼운 빠른 민감도 결과다. full retrain 결과가 아니다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +4.58% |
| Local ESS SAC (no P2P) | 135.004 | -4.38% | +0.00% |
| Soft-MILP P2P + local SAC | 133.211 | -5.65% | -1.33% |
| Forecast-based Shared PI-SAC | 115.362 | -18.29% | -14.55% |
| Forecast rolling MILP | 97.050 | -31.26% | -28.11% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -44.06% |

## EV Transformer Shape Calibration Full Retrain

이 표는 shape-calibrated train/test CSV로 하위 no-P2P PI-SAC와 상위 Shared
PI-SAC를 모두 다시 학습한 seed1 결과다. 메인 3-seed headline은 아니지만,
Transformer 계열 중에서는 가장 강한 후보 결과다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +7.27% |
| Local ESS SAC (no P2P) | 131.624 | -6.78% | +0.00% |
| Soft-MILP P2P + local SAC | 128.341 | -9.10% | -2.49% |
| Forecast-based Shared PI-SAC | 113.278 | -19.77% | -13.94% |
| Forecast rolling MILP | 97.050 | -31.26% | -26.27% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -42.63% |

읽는 법:

- uncalibrated Transformer seed1 Shared PI-SAC `116.396M`보다 `3.118M` 낮다.
- shape-cal existing-policy sensitivity `115.362M`보다 `2.084M` 낮다.
- accepted main 3-seed 평균 `117.369M`보다 낮지만, 이 결과는 seed1 단일이다.
- 기존 EV v1 seed1 best `112.841M`보다는 `0.437M` 높아서 교체 확정은 아니다.

## EV Transformer Shape Calibration 3-Seed

이 표는 같은 shape-calibrated EV Transformer 후보를 seed1, seed2, seed42로
확장한 3-seed 평균 결과다. PV는 기존 tree v5를 유지했고, forecast_peakrisk
관측과 Shared PI-SAC 상위 정책을 그대로 사용했다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +7.84% |
| Local ESS SAC (no P2P) | 131.961 | -6.54% | +0.00% |
| Soft-MILP P2P + local SAC | 129.598 | -8.21% | -1.79% |
| Forecast-based Shared PI-SAC | 113.858 | -19.36% | -13.74% |
| Forecast rolling MILP | 97.050 | -31.26% | -25.02% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -42.77% |

읽는 법:

- current main 3-seed Shared PI-SAC `117.369M`보다 `3.511M` 낮다.
- current main 3-seed local no-P2P 대비 개선폭 `-8.40%`보다 크고, 이번 결과는 `-13.74%`다.
- Soft-MILP P2P + local SAC는 local 대비 `-1.79%`라서, 이번에도 SAC-SAC 공유 정책 쪽이 더 강하다.
- Forecast rolling MILP `97.050M`과 Hindsight MILP `75.519M`은 여전히 상한/기준선 역할이다.

## EV Transformer Shape Calibration Lookahead 3-Seed

이 표는 같은 shape-calibrated EV Transformer 후보에서 하위 no-P2P 관측을
`forecast_peakrisk` 대신 `forecast_lookahead`로 바꿔 seed1, seed2, seed42
평균을 다시 검증한 결과다. local no-P2P는 좋아졌지만, 공유 상위 정책의
추가 개선폭은 peakrisk 3-seed보다 작아졌다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +13.82% |
| Local ESS SAC (no P2P) | 124.050 | -12.14% | +0.00% |
| Soft-MILP P2P + local SAC | 122.500 | -13.24% | -1.25% |
| Forecast-based Shared PI-SAC | 116.311 | -17.62% | -6.24% |
| Forecast rolling MILP | 97.050 | -31.26% | -21.77% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -39.12% |

읽는 법:

- accepted main 3-seed Shared PI-SAC `117.369M`보다는 `1.058M` 낮다.
- shape-cal peakrisk 3-seed Shared PI-SAC `113.858M`보다는 `2.453M` 높다.
- local no-P2P는 shape-cal peakrisk 3-seed `131.961M`보다 `7.911M` 낮아졌다.
- 별도 lower-only sensitivity 파일의 `110.437M`은 직접 하위만 굴린 참고값이고, apples-to-apples 5-method 표에는 corrected tariff 환경의 `124.050M`을 쓴다.

## EV Transformer Share-Aware Lower Probe

이 표는 `forecast_lookahead` 하위 SAC를 no-share가 아니라 soft-MILP 공유
입력을 보면서 다시 학습한 seed1 단일 probe다. 공유가 들어왔을 때의 반응성은
좋아졌지만, no-share local baseline이 크게 나빠져 최종 후보로는 보류한다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +2.91% |
| Local ESS SAC (no P2P) | 137.200 | -2.83% | +0.00% |
| Soft-MILP P2P + local SAC | 134.801 | -4.53% | -1.75% |
| Forecast-based Shared PI-SAC | 117.722 | -16.62% | -14.20% |
| Forecast rolling MILP | 97.050 | -31.26% | -29.26% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -44.96% |

읽는 법:

- shared vs local 개선폭은 `-14.20%`라서 공유 반응성 자체는 회복됐다.
- 하지만 local no-P2P가 `124.050M`에서 `137.200M`으로 악화됐다.
- 최종 shared도 lookahead 3-seed `116.311M`, peakrisk 3-seed `113.858M`보다 높다.
- 다음 share-aware 실험은 no-share/zero-share episode를 섞어 local baseline을 보호해야 한다.

## EV Transformer Mixed Share-Aware Lower Probe

이 표는 `forecast_lookahead` 하위 SAC를 soft-MILP 공유 65%와 zero-share
35% episode로 섞어 다시 학습한 seed1 단일 probe다. soft-MILP-only
share-aware probe에서 무너진 local baseline을 회복하면서 공유 개선폭도
유지했다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +12.19% |
| Local ESS SAC (no P2P) | 125.849 | -10.87% | +0.00% |
| Soft-MILP P2P + local SAC | 125.447 | -11.15% | -0.32% |
| Forecast-based Shared PI-SAC | 110.648 | -21.63% | -12.08% |
| Forecast rolling MILP | 97.050 | -31.26% | -22.88% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -39.99% |

읽는 법:

- seed1 단일 기준으로 Transformer 계열 중 가장 낮은 Shared PI-SAC 비용이다.
- soft-MILP-only share-aware probe보다 local no-P2P가 `137.200M`에서 `125.849M`으로 회복됐다.
- Shared PI-SAC도 `117.722M`에서 `110.648M`으로 내려갔다.
- 아직 seed1 단일이므로 headline 교체 전에는 seed2/seed42 반복 검증이 필요하다.

## EV Transformer Mixed Share-Aware Lower 3-Seed

이 표는 위 seed1 probe를 seed1, seed2, seed42로 확장한 평균 결과다.
seed1 단일에서는 매우 강했지만, 3-seed 평균에서는 기존 shape-cal peakrisk
3-seed보다 약해졌다. 따라서 headline 교체 후보라기보다 "share-aware lower는
seed별 분산이 크다"는 근거로 기록한다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +10.10% |
| Local ESS SAC (no P2P) | 128.236 | -9.18% | +0.00% |
| Soft-MILP P2P + local SAC | 127.946 | -9.38% | -0.23% |
| Forecast-based Shared PI-SAC | 118.678 | -15.95% | -7.45% |
| Forecast rolling MILP | 97.050 | -31.26% | -24.32% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -41.11% |

읽는 법:

- seed1 단일 Shared PI-SAC `110.648M`은 3-seed 평균에서 `118.678M`으로 약해졌다.
- mixed lower는 local no-P2P를 `128.236M`까지 회복했지만, lookahead 3-seed local `124.050M`보다는 높다.
- shared vs local 개선폭은 `-7.45%`로 살아 있지만, lookahead 3-seed `116.311M`과 peakrisk 3-seed `113.858M`보다 최종 shared 비용이 높다.
- 결론: zero-share episode를 섞는 아이디어는 seed1에는 유효했지만, 현재 설정 그대로 headline으로 쓰기에는 multi-seed 안정성이 부족하다.

## EV Transformer v2 Peak-Aware p90 Seed1

이 표는 peak-aware loss로 다시 만든 EV Transformer v2에 validation 기반
`demand_p90`를 추가하고, 하위 관측은 `forecast_peakrisk`, 상위 관측은
`peak_queue_forecast`로 학습한 seed1 단일 결과다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +21.38% |
| Local ESS SAC (no P2P) | 116.325 | -17.61% | +0.00% |
| Soft-MILP P2P + local SAC | 114.447 | -18.94% | -1.61% |
| Forecast-based Shared PI-SAC | 115.408 | -18.26% | -0.79% |
| Forecast rolling MILP | 122.976 | -12.90% | +5.72% |
| Hindsight MILP upper bound | 105.356 | -25.38% | -9.43% |

읽는 법:

- Shared PI-SAC `115.408M`은 accepted main 3-seed Shared PI-SAC `117.369M`보다 `1.961M` 낮다.
- 다만 local no-P2P가 이미 `116.325M`까지 좋아져서, P2P 공유 추가 개선폭은 `-0.79%`로 작다.
- 따라서 이 결과는 "Transformer를 쓰면서 total을 낮추는 후보"로는 의미가 있지만, "공유 효과가 크게 보인다"는 주장에는 약하다.
- 현재 같은 설정에서 no-p90 full peakrisk seed1은 Shared PI-SAC `119.651M`, local `131.222M`이었다.

## EV Transformer v2 p90 Share-Aware Fine-Tune Seed1

이 표는 위 p90 no-share lower에서 시작해 하위 SAC를 100k step만 추가
fine-tune한 seed1 단일 sanity 결과다. 처음 나온 `zero_sum` 공유 제약 결과는
총액이 너무 낮아 물리 제약을 다시 확인했다. 결론은 `zero_sum` 결과를 headline
후보로 쓰면 안 된다는 쪽이다.

| setting | Shared PI-SAC total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 | share/day |
|---|---:|---:|---:|
| `zero_sum` | 106.594 | -24.50% | -10.09% | 4461 |
| `pv_ess` | 117.343 | -16.89% | -1.03% | 417 |
| `pv_only` | 117.923 | -16.48% | -0.54% | 174 |

읽는 법:

- `zero_sum`은 충전소 간 공유량 합만 0이면 되는 느슨한 제약이라 `106.594M`까지 내려갔다.
- 같은 lower와 같은 상위 학습 조건에서 물리 공유 제약을 걸면 `pv_ess`는 `117.343M`, `pv_only`는 `117.923M`이다.
- 따라서 `106.594M`은 과대평가로 기록하고, 방어 가능한 seed1 sanity 값은 `117M`대다.
- `pv_ess`는 accepted main 3-seed Shared PI-SAC `117.369M`과 거의 같은 수준이다.

## Refresh Command

프로젝트 루트에서 실행한다.

```bash
python3 ai/ai_labs/scripts/check_experiment_artifacts.py --strict
```
