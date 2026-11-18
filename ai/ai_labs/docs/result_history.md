# Result History

이 문서는 완료된 주요 실험 흐름을 짧게 정리한다. 숫자는 현재 commit 전
정리 기준이며, 최신 artifact가 바뀌면 `ai/ai_labs/scripts/check_experiment_artifacts.py`
출력과 함께 다시 확인한다.

현재 프론트/제출 보고서 기준 최종 비교 수치는 PV
`tree_v5_hgb_absolute_error`와 EV Transformer v2 peak-aware
shape-calibrated p90를 사용한 EV-only volume-moderate physical P2P
3-seed 결과다. 최신 source of truth는
`five_method_comparison_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42_physical_oracle.json`이며,
자세한 표는 `ai_labs/results/README.md`의 "Frontend / Report Final
Numbers"를 본다.

## 1. 초기 PV/EV forecast observation

초기에는 PV/EV 예측값을 붙인 strict forecast setting으로 의사결정 모델을
검증했다. 이 과정에서 두 가지 문제가 분리됐다.

- 예측값을 붙이면 실제값을 보는 oracle setting보다 성능이 떨어진다.
- 특히 PV TFT 계열은 제주 Jan-Feb 구간에서 tree 모델보다 WAPE가 컸다.

결론:

- 의사결정 모델을 평가할 때는 `forecast` 입력과 `actual` 정산을 분리해야 한다.
- PV는 TFT 후보를 계속 보되, 완료 결과 기준으로는 tree v5를 메인으로 쓴다.

## 2. PV 모델 비교

Jan-Feb 기준 결과:

| PV 후보 | 시간별 WAPE | 일별 WAPE | 판단 |
|---|---:|---:|---|
| `tft_v3` | 20.93% | 16.04% | 미채택 |
| `tft24x9_v6` | 22.04% | 13.77% | 미채택 |
| `tft24x9_cyclic_v6` | 22.06% | 14.70% | 미채택 |
| `tree_v5_hgb_absolute_error` | 12.01% | 4.98% | 현재 채택 |

TFT가 이론적으로 나쁘다는 뜻은 아니다. 현재 데이터 규모와 feature 구조에서는
tree가 더 안정적이었다.

## 3. EV 모델 비교

EV는 복잡한 딥러닝보다 요일/시간 반복성이 강했다.

| EV 후보 | 시간별 WAPE | Bias | RMSE | 판단 |
|---|---:|---:|---:|---|
| `same_dow_4w_hour_mean` | 11.78% | -0.03% | 152.48 | 메인 사용 |
| `same_dow_4w_hour_p90_winsor_mean` | 9.38% | -2.79% | 59.50 | 예측 개선 후보 |
| `ev_shape_transformer` | 9.77% | -0.03% | 43.57 | Transformer 후보. seed1 의사결정 검증 완료 |

EV v3 p90-winsor는 예측 자체는 개선했다. 다만 의사결정 seed1 재학습에서
local no-P2P baseline이 약해져서 메인 교체는 보류했다.

EV Transformer 후보는 WAPE만 보면 v3보다 약간 높지만, RMSE와 bias는 더
안정적이었다. seed1 의사결정 검증에서는 shared total@8320이 `116.396M KRW`로
local no-P2P 대비 `-14.39%`였다. 아직 3-seed 평균이 아니므로 메인 결과로
교체하지 않고 후보 결과로 기록한다.

추가로 train 마지막 60일 validation 구간만 사용해 station-hour shape
calibration을 적용했다. 일별 총량은 보존했고, test 실제값은 보정에 쓰지
않았다. Jan-Feb EV WAPE는 `9.77% -> 8.90%`, RMSE는 `43.57 -> 40.11`로
개선됐다. 기존 uncalibrated policy에 test CSV만 바꿔 끼운 빠른 민감도
평가에서는 Shared PI-SAC total@8320이 `116.396M -> 115.362M`으로 내려갔다.
다만 기존 EV v1 seed1 best `112.841M`보다는 높아서, 메인 교체 전 full
retrain과 3-seed 검증이 필요하다.

Full retrain까지 돌리면 하위 no-P2P와 상위 Shared PI-SAC 모두 shape-calibrated
CSV에 맞춰 다시 학습된다. 이 결과에서는 Shared PI-SAC total@8320이
`113.278M KRW`까지 내려갔다. uncalibrated Transformer seed1 `116.396M`,
shape-cal existing-policy `115.362M`, accepted 3-seed 평균 `117.369M`보다는
낮다. 하지만 기존 EV v1 seed1 best `112.841M`보다 `0.437M` 높아서,
현재 판단은 "Transformer를 유지해야 할 때 쓸 수 있는 강한 seed1 후보"다.
메인 headline으로 교체하려면 3-seed 검증이 필요했다.

3-seed까지 확장하면 Shared PI-SAC total@8320은 `113.858M KRW`다.
이는 accepted main 3-seed `117.369M KRW`보다 `3.511M KRW` 낮고,
local no-P2P 대비 개선폭도 accepted main `-8.40%`에서 `-13.74%`로 커진다.
따라서 Transformer 방향을 유지해야 한다면, seed1 단일 후보가 아니라
shape-calibrated Transformer 3-seed 결과를 더 방어 가능한 후보로 본다.

## 4. 메인 3-seed 의사결정 결과

메인 결과는 PV tree v5 + EV v1 + forecast_peakrisk 관측 + Shared PI-SAC
상위 정책 기준이다.

| method | total@8320 M KRW | grid-only 대비 | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|---:|
| Grid-only default | 188.732 | +0.00% | +33.67% | +47.29% |
| Passive-PV default | 141.192 | -25.19% | +0.00% | +10.19% |
| Local ESS SAC (no P2P) | 128.136 | -32.11% | -9.25% | +0.00% |
| Forecast-based Shared PI-SAC | 117.369 | -37.81% | -16.87% | -8.40% |
| Forecast rolling MILP | 122.100 | -35.31% | -13.52% | -4.71% |
| Hindsight MILP upper bound | 105.356 | -44.18% | -25.38% | -17.78% |

가장 방어 가능한 문장:

> Local ESS control without P2P reduces total bill by 9.25% versus passive-PV
> default. Adding forecast-based learned P2P sharing reduces total bill by
> 16.87% versus passive-PV default and by 8.40% versus the local no-P2P baseline.

논문식 grid-only baseline으로 보면 Shared PI-SAC는 `-37.81%`다.

## 5. Soft-MILP P2P + local SAC

Soft-MILP P2P + local SAC는 상위 공유량을 수학 최적화로 계산하고, 하위 ESS는
SAC가 처리하는 구조다.

결과는 local no-P2P 대비 `+0.96%`로 약간 나빴다. 이것 때문에 "MILP를 붙이면
무조건 좋아진다"라고 말하면 안 된다.

해석:

- 공유량만 수학 최적화해도 하위 ESS 정책과 맞지 않으면 손해가 날 수 있다.
- 현재 성과는 상위/하위가 함께 학습된 `SAC + SAC` 쪽이 더 방어 가능하다.

## 6. Forecast rolling MILP와 Hindsight MILP

MILP는 두 종류를 분리해야 한다.

| 이름 | 해석 |
|---|---|
| Forecast rolling MILP | 예측값으로 계획하고 실제값으로 정산하는 배포 가능한 baseline |
| Hindsight MILP upper bound | 미래 실제값을 알고 푸는 이론적 상한선 |

Forecast rolling MILP는 total@8320 기준 `122.100M KRW`이고, Shared PI-SAC는
`117.369M KRW`다. 즉 현재 메인 결과에서는 Shared PI-SAC가 usable MILP
baseline보다 낮다.

Hindsight MILP는 `105.356M KRW`지만, 미래 실제 PV/EV를 알고 계산한 값이라
모델 성능으로 주장하면 안 된다.

## 6-1. physical P2P sanity check

기존 메인 3-seed는 상위 공유 projection이 `zero_sum`이었다. 이는 충전소
전체 공유량 합은 0으로 맞추지만, export하는 충전소가 실제 PV 잉여나 ESS
여유를 가지고 있는지는 직접 제한하지 않는다. 따라서 물리 P2P 성능으로
주장하기 전에 `pv_ess`와 `pv_only`로 다시 검증했다.

| setting | Shared PI-SAC total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 | share/day |
|---|---:|---:|---:|---:|
| original `zero_sum` | 117.369 | -16.87% | -8.40% | 3773 |
| `pv_ess` | 125.547 | -11.08% | -2.02% | 427 |
| `pv_only` | 127.447 | -9.73% | -0.54% | 121 |

결론은 `zero_sum` headline을 물리 P2P 결과로 그대로 쓰면 안 된다는 것이다.
방어 가능한 공유 효과는 PV 잉여와 ESS 여유 export를 허용하는 `pv_ess`
기준 local 대비 `-2.02%` 정도다. `pv_only`는 더 보수적인 같은시간 PV 잉여
공유 기준이며, local 대비 `-0.54%`로 작다.

## 7. EV Transformer 후보 seed1 검증

팀원이 준 Transformer 방향을 살리기 위해 EV 수요 모양을 예측하는
`ev_shape_transformer` 후보를 만들고, PV는 기존 tree v5를 유지해서 seed1
의사결정까지 검증했다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +3.85% |
| Local ESS SAC (no P2P) | 135.955 | -3.71% | +0.00% |
| Soft-MILP P2P + local SAC | 133.299 | -5.59% | -1.95% |
| Forecast-based Shared PI-SAC | 116.396 | -17.56% | -14.39% |
| Forecast rolling MILP | 97.493 | -30.95% | -28.29% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -44.45% |

이 결과는 공유 정책 개선폭은 좋지만 seed1 단일 검증이다. 메인 결과로
쓰기보다는 Transformer를 유지해야 할 때 쓸 수 있는 후보 결과로 본다.

Shape calibration 민감도에서는 같은 기존 정책 기준으로 다음처럼 바뀌었다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +4.58% |
| Local ESS SAC (no P2P) | 135.004 | -4.38% | +0.00% |
| Soft-MILP P2P + local SAC | 133.211 | -5.65% | -1.33% |
| Forecast-based Shared PI-SAC | 115.362 | -18.29% | -14.55% |
| Forecast rolling MILP | 97.050 | -31.26% | -28.11% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -44.06% |

Shape calibration full retrain 결과는 다음과 같다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +7.27% |
| Local ESS SAC (no P2P) | 131.624 | -6.78% | +0.00% |
| Soft-MILP P2P + local SAC | 128.341 | -9.10% | -2.49% |
| Forecast-based Shared PI-SAC | 113.278 | -19.77% | -13.94% |
| Forecast rolling MILP | 97.050 | -31.26% | -26.27% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -42.63% |

full retrain에서는 local no-P2P가 existing-policy 민감도 `135.004M`에서
`131.624M`으로 회복됐고, Shared PI-SAC도 `115.362M`에서 `113.278M`으로
개선됐다. Soft-MILP P2P + local SAC는 local 대비 `-2.49%`에 그친 반면,
SAC-SAC Shared PI-SAC는 local 대비 `-13.94%`까지 벌어졌다. 따라서
Transformer 방향을 설명해야 한다면 이 표가 기존 `evtfm_v1`보다 방어 가능하다.

3-seed shape-calibrated Transformer 결과는 다음과 같다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +7.84% |
| Local ESS SAC (no P2P) | 131.961 | -6.54% | +0.00% |
| Soft-MILP P2P + local SAC | 129.598 | -8.21% | -1.79% |
| Forecast-based Shared PI-SAC | 113.858 | -19.36% | -13.74% |
| Forecast rolling MILP | 97.050 | -31.26% | -25.02% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -42.77% |

이 결과는 accepted main 3-seed보다 shared total@8320이 낮고, 공유 개선폭도
더 크다. 다만 EV 모델을 바꾼 결과이므로 최종 메인 교체 여부는
"EV Transformer를 채택한다"는 설명과 함께 결정해야 한다.

Forecast lookahead 하위 관측으로 다시 돌린 3-seed 결과는 다음과 같다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +13.82% |
| Local ESS SAC (no P2P) | 124.050 | -12.14% | +0.00% |
| Soft-MILP P2P + local SAC | 122.500 | -13.24% | -1.25% |
| Forecast-based Shared PI-SAC | 116.311 | -17.62% | -6.24% |
| Forecast rolling MILP | 97.050 | -31.26% | -21.77% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -39.12% |

이 실험은 local no-P2P 약점을 줄이는 데는 성공했다. corrected 5-method
기준 local이 `131.961M`에서 `124.050M`으로 낮아졌다. 하지만 공유 상위까지
붙인 최종 Shared PI-SAC는 `113.858M`에서 `116.311M`으로 올라가서
peakrisk 3-seed보다 약하다. 따라서 Transformer 계열 headline 후보는
아직 shape-cal peakrisk 3-seed가 더 좋고, lookahead는 local 하위 안정화
후속 근거로 기록한다. 별도 lower-only sensitivity의 `110.437M`은 직접
하위만 굴린 참고값이므로 최종 표에는 corrected 5-method 기준 `124.050M`을
사용한다.

Share-aware lower probe는 `forecast_lookahead` 하위 SAC를 soft-MILP 공유
입력으로 다시 학습한 seed1 단일 실험이다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +2.91% |
| Local ESS SAC (no P2P) | 137.200 | -2.83% | +0.00% |
| Soft-MILP P2P + local SAC | 134.801 | -4.53% | -1.75% |
| Forecast-based Shared PI-SAC | 117.722 | -16.62% | -14.20% |
| Forecast rolling MILP | 97.050 | -31.26% | -29.26% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -44.96% |

이 probe는 공유 입력 대응에는 성공했지만 최종 채택 후보는 아니다. Shared
PI-SAC가 local 대비 `-14.20%`까지 벌어진 것은 긍정적이지만, local no-P2P가
`124.050M`에서 `137.200M`으로 무너졌다. 즉 soft-MILP 공유만 보고 하위를
학습시키면 공유 상황에는 강해지지만 zero-share 상황의 ESS 운용 능력이
희생된다. 다음 실험은 share-aware lower를 유지하되 no-share/zero-share
episode를 섞는 방식으로 local baseline을 보호해야 한다.

Mixed share-aware lower probe는 위 가설을 확인하기 위해 soft-MILP 공유
episode 65%와 zero-share episode 35%를 섞어 하위 SAC를 다시 학습한 seed1
단일 실험이다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +12.19% |
| Local ESS SAC (no P2P) | 125.849 | -10.87% | +0.00% |
| Soft-MILP P2P + local SAC | 125.447 | -11.15% | -0.32% |
| Forecast-based Shared PI-SAC | 110.648 | -21.63% | -12.08% |
| Forecast rolling MILP | 97.050 | -31.26% | -22.88% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -39.99% |

이 결과는 방향이 맞다는 강한 신호다. local no-P2P는 soft-MILP-only
share-aware `137.200M`에서 `125.849M`으로 회복됐고, Shared PI-SAC는
`117.722M`에서 `110.648M`으로 낮아졌다. 다만 seed1 단일 결과이므로
최종 headline으로 쓰려면 seed2/seed42까지 반복해서 3-seed 평균을 확인해야
한다.

Mixed share-aware lower를 seed1, seed2, seed42로 확장하면 결과는 다음과
같다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +10.10% |
| Local ESS SAC (no P2P) | 128.236 | -9.18% | +0.00% |
| Soft-MILP P2P + local SAC | 127.946 | -9.38% | -0.23% |
| Forecast-based Shared PI-SAC | 118.678 | -15.95% | -7.45% |
| Forecast rolling MILP | 97.050 | -31.26% | -24.32% |
| Hindsight MILP upper bound | 75.519 | -46.51% | -41.11% |

3-seed 평균에서는 seed1 단일의 강한 `110.648M` 결과가 유지되지 않았다.
local no-P2P는 `128.236M`으로 soft-MILP-only share-aware보다 훨씬 낫지만,
lookahead 3-seed local `124.050M`보다 높고, Shared PI-SAC도 lookahead
3-seed `116.311M`과 peakrisk 3-seed `113.858M`보다 높다. 따라서 이 실험은
"zero-share episode 혼합이 local 붕괴를 줄인다"는 부분 가설은 지지하지만,
현재 `0.35` 혼합비와 soft-MILP share-aware lower를 headline으로 채택할
근거는 부족하다고 기록한다.

EV Transformer v2에서는 peak-hour/daily-peak 오차를 줄이는 loss를 추가하고,
validation 기반 `demand_p90` 컬럼을 실제 CSV와 런타임 day data까지 전달했다.
seed1 단일 결과는 다음과 같다.

| method | total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|
| Passive-PV default | 141.192 | +0.00% | +21.38% |
| Local ESS SAC (no P2P) | 116.325 | -17.61% | +0.00% |
| Soft-MILP P2P + local SAC | 114.447 | -18.94% | -1.61% |
| Forecast-based Shared PI-SAC | 115.408 | -18.26% | -0.79% |
| Forecast rolling MILP | 122.976 | -12.90% | +5.72% |
| Hindsight MILP upper bound | 105.356 | -25.38% | -9.43% |

이 결과는 accepted main 3-seed Shared PI-SAC `117.369M`보다 낮다. 하지만
개선의 대부분은 local no-P2P가 `116.325M`으로 강해진 데서 나오며, Shared
PI-SAC의 local 대비 추가 효과는 `-0.79%`로 작다. 따라서 현재 해석은
"Transformer v2 + calibrated p90가 local 운영을 크게 개선했다"이고,
"P2P 공유 효과가 크게 커졌다"는 결론은 아직 아니다. 공유 효과를 확인하기
위해 no-share lower에서 시작하는 share-aware fine-tune probe를 후속으로
돌린다.

share-aware fine-tune probe는 위 p90 no-share lower에서 시작해 하위 SAC를
100k step 추가 학습했다. 처음 `zero_sum` 공유 제약으로 돌린 결과는 매우
강했지만, 물리 제약 sanity check에서 과대평가로 판정했다.

| setting | Shared PI-SAC total@8320 M KRW | passive-PV 대비 | local no-P2P 대비 | share/day |
|---|---:|---:|---:|
| `zero_sum` | 106.594 | -24.50% | -10.09% | 4461 |
| `pv_ess` | 117.343 | -16.89% | -1.03% | 417 |
| `pv_only` | 117.923 | -16.48% | -0.54% | 174 |

`zero_sum`은 충전소 간 공유량 합만 0이면 되므로 share/day가 `4461 kWh/day`까지
커졌다. 반면 PV 잉여와 ESS 여유를 내보내는 `pv_ess`에서는 `417 kWh/day`,
동시간 PV 잉여만 허용하는 `pv_only`에서는 `174 kWh/day`로 줄었다. 따라서
`106.594M`은 물리 공유 제약을 통과한 성능으로 보지 않는다. 방어 가능한
sanity 결과는 `pv_ess` 기준 `117.343M`이며, 이는 accepted main 3-seed
Shared PI-SAC `117.369M`과 거의 같은 수준이다.

## 7-1. EV-only demand asymmetry physical P2P sensitivity

기존 main physical P2P sanity에서는 `pv_ess` 공유 효과가 local 대비
`-2.02%`로 작았다. 원인은 공유 정책 자체보다 충전소별 PV/EV profile에서
실제로 내보낼 수 있는 잉여와 받을 수 있는 수요가 동시에 충분하지 않은
구조일 수 있다. 이를 확인하기 위해 PV는 그대로 두고 EV 수요만 충전소별로
다르게 재배치한 EV-only 민감도 시나리오를 만들었다.

seed1 screening에서는 `volume_moderate`가 가장 균형이 좋았다. `volume_strong`은
공유량은 크지만 총비용 best는 아니었고, `shape_strong`은 공유 효과가 작았다.
최종으로 `volume_moderate`를 seed1, seed2, seed42까지 확장했다.

이 시나리오는 `grid-only` 대비 절감률과 `passive-PV default` 대비 절감률을
분리해서 봐야 한다. `grid-only` 대비 값에는 PV 도입 효과가 포함되므로,
교수님 PI-SAC 단일 충전소 논문 수치와 직접 비교하지 않는다.

| method | total@8320 M KRW | grid-only 대비 | passive-PV 대비 | local no-P2P 대비 | share/day |
|---|---:|---:|---:|---:|---:|
| Grid-only/no-PV | 198.663 | +0.00% | +51.27% | +70.50% | 0 |
| Passive-PV default | 131.333 | -33.89% | +0.00% | +12.71% | 0 |
| Local ESS SAC (no P2P) | 116.520 | -41.35% | -11.28% | +0.00% | 0 |
| Soft-MILP P2P + local SAC | 115.053 | -42.09% | -12.40% | -1.26% | 553 |
| Forecast-based Shared PI-SAC | 110.703 | -44.28% | -15.71% | -4.99% | 977 |
| Forecast rolling MILP | 111.958 | -43.64% | -14.75% | -3.92% | 1378 |
| Hindsight MILP upper bound | 95.559 | -51.90% | -27.24% | -17.99% | 1720 |

이 결과는 물리 제약이 걸린 `pv_ess` 공유에서도 EV 수요 비대칭이 충분하면
Forecast-based Shared PI-SAC가 local no-P2P 대비 `-4.99%`, passive-PV default
대비 `-15.71%`까지 내려갈 수 있음을 보여준다. Forecast rolling MILP
`111.958M`보다도 낮다.

다만 이 값은 EV 수요를 재배치한 민감도 시나리오다. 따라서 기존 main
headline을 직접 대체하지 않는다. 발표에서는 "우리 방법이 물리 P2P 공유로
효과를 내려면 충전소별 수요 shape/volume 차이가 있어야 하며, 그 조건에서는
3-seed 평균에서도 local 대비 약 5% 추가 절감이 나온다"는 근거로 쓰는 것이
가장 방어 가능하다.

## 8. sharealign_v1 민감도 실험

sharealign_v1은 공유 기회가 부족한지 확인하기 위한 별도 시나리오다.

| 지표 | 메인 strict forecast | sharealign_v1 |
|---|---:|---:|
| same-hour shareable overlap | 332 kWh/day | 3732 kWh/day |
| surplus/deficit 동시 발생 시간 | 3.19 h/day | 9.12 h/day |
| 즉시 공유 가능 에너지 가치 | 2.44M KRW | 34.15M KRW |

이 실험은 메인 성과표가 아니라 민감도 설명용이다. 공유 기회가 커지면
planner/hybrid 계열이 강해질 수 있다는 후속 방향을 보여준다.

## 9. 현재 보류/후속 과제

| 과제 | 이유 |
|---|---|
| PV safe-lag/TFT 추가 검증 | tree v5는 성능은 좋지만 strict day-ahead 조건에서 방어가 필요 |
| EV v3 multi-seed 의사결정 | 예측은 좋아졌지만 local baseline 안정성 확인 필요 |
| 제주 EV station 기반 3-arm 재구성 | KEPCO 시설유형보다 지역 일관성이 좋아질 수 있음 |
| sharealign/hybrid planner | 공유 기회가 충분한 scenario에서 SAC upper 개선 여지 |
