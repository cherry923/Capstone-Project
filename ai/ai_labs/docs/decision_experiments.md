# Decision Experiment Guide

이 문서는 ESS/P2P 의사결정 실험을 설명한다.

## 전체 구조

의사결정은 두 단계다.

| 단계 | 역할 | 현재 모델 |
|---|---|---|
| 하위 정책 | 각 station의 ESS 충방전 결정 | PI-SAC lower |
| 상위 정책 | station 사이의 전력 공유량 결정 | Shared PI-SAC upper |

하위 모델은 station 0, 1, 2를 따로 학습한다. 상위 모델은 세 station의
상태를 보고 공유량 vector를 낸다. 공유량은 전체 합이 0이 되도록 맞춘다.
즉 한 station이 받으면 다른 station은 그만큼 내보내는 구조다.

## 비교하는 운영 방식

현재 메인 표는 다음 운영 방식을 비교한다.

| 이름 | 쉽게 말하면 | 하위 | 상위 |
|---|---|---|---|
| Grid-only default | PV/ESS/P2P 없이 grid에서 전부 구매 | 없음 | 없음 |
| Passive-PV default | 같은 station PV만 즉시 사용, ESS/P2P 없음 | 없음 | 없음 |
| Local ESS SAC (no P2P) | station별 ESS만 AI가 제어 | PI-SAC | 없음 |
| Soft-MILP P2P + local SAC | 공유량은 수학 최적화, ESS는 SAC | PI-SAC | Soft-MILP |
| Forecast-based Shared PI-SAC | 공유량도 SAC, ESS도 SAC | PI-SAC | Shared PI-SAC |
| Forecast rolling MILP | 예측값으로 수학 최적화 운영 | MILP | MILP |
| Hindsight MILP upper bound | 미래 실제값을 알고 푼 이론적 상한선 | MILP | MILP |

`SAC + SAC`라고 말할 때는 `Forecast-based Shared PI-SAC`를 뜻한다.
상위 공유 정책도 SAC이고, 하위 ESS 정책도 SAC라는 의미다.

## MILP를 쉽게 설명하기

MILP는 "정답 모델"이라기보다는 수학 최적화 기준값이다.

쉽게 말하면:

> 주어진 제약 조건 안에서 전기요금이 가장 작아지도록 충방전과 공유량을
> 계산하는 수학 최적화 방법이다.

다만 MILP도 두 종류를 구분해야 한다.

| 이름 | 미래 실제값을 아는가 | 용도 |
|---|---|---|
| Forecast rolling MILP | 모름. 예측값으로 계획하고 실제값으로 정산 | 배포 가능한 비교 baseline |
| Hindsight MILP upper bound | 앎. 실제 PV/EV를 보고 사후 최적화 | 이론적 상한선 |

따라서 "실제 수요와 태양광을 모두 알고 계산한 이론적 기준값"은
`Hindsight MILP upper bound`다. 이건 실사용 모델이 아니라 상한선이다.

## 현재 메인 결과

조건:

- PV/EV forecast observation.
- PV: `tree_v5_hgb_absolute_error`.
- EV: `evtfm_v2_peakaware_shapecal_p90`.
- 시나리오: EV-only volume-moderate physical P2P.
- 평가 기간: 2022-01-01 ~ 2022-02-28.
- seed: 1, 2, 42 평균.
- 기본요금 단가: 8,320 KRW/kW-month.

| method | total@8320 M KRW | net M KRW | demand charge M KRW | grid-only 대비 | passive-PV 대비 | local no-P2P 대비 | peak_v | share/day |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Grid-only default | 198.663 | 164.177 | 34.486 | +0.00% | +51.27% | +70.50% | 7744.8 | 0 |
| Passive-PV default | 131.333 | 98.230 | 33.103 | -33.89% | +0.00% | +12.71% | 3611.5 | 0 |
| Local ESS SAC (no P2P) | 116.520 | 85.950 | 30.570 | -41.35% | -11.28% | +0.00% | 424.7 | 0 |
| Soft-MILP P2P + local SAC | 115.053 | 84.920 | 30.133 | -42.09% | -12.40% | -1.26% | 393.2 | 553 |
| Forecast-based Shared PI-SAC | 110.703 | 82.369 | 28.334 | -44.28% | -15.71% | -4.99% | 167.5 | 977 |
| Forecast rolling MILP | 111.958 | 83.926 | 28.032 | -43.64% | -14.75% | -3.92% | 51.7 | 1378 |
| Hindsight MILP upper bound | 95.559 | 78.602 | 16.957 | -51.90% | -27.24% | -17.99% | 0.0 | 1720 |

핵심 해석:

- Passive-PV default의 `-33.89%`는 AI 효과가 아니라 같은 station PV
  자가소비 효과다.
- Local ESS SAC의 `-11.28%`는 공유 효과가 아니라 station별 ESS 제어 효과다.
- Shared PI-SAC의 local no-P2P 대비 `-4.99%`가 P2P 공유를 추가한 효과다.
- Forecast rolling MILP는 배포 가능한 수학 최적화 baseline이고, 현재
  Shared PI-SAC가 total@8320 기준으로 더 낮다.
- Hindsight MILP는 미래 실제값을 아는 상한선이라 모델 성과로 주장하면 안 된다.

## 평가 지표 설명

| 지표 | 의미 |
|---|---|
| `net` | 전력량 요금, ESS degradation, 공유 비용 등을 합친 운영비 |
| `demand charge` | 계약전력/피크 성격의 기본요금 |
| `total@8320` | `net + demand charge` |
| `contract avg` | 월별 기본요금 계산에 쓰는 평균 계약전력 수준 |
| `peak_v` | 시간별 grid import가 peak limit을 초과한 양의 합 |
| `share/day` | 하루 평균 station 간 공유 전력량 |

peak violation은 "전기를 구매했다"는 뜻이 아니다. 예를 들어 peak limit이
600 kW인데 어떤 시간의 grid import가 650 kW면 그 시간의 peak violation은
50으로 잡힌다.

SOC violation은 ESS 용량/상태 제약 위반이다. 현재 SAC 평가에서는 환경의
projection과 제약 처리 때문에 보고상 `0.0`으로 보는 것이 맞다.

## 주요 artifact

| artifact | 경로 |
|---|---|
| 최종 5-method source JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42_physical_oracle.json` |
| corrected tariff source JSON | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42.json` |
| 최종 비교 CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_test.csv` |
| 프론트 graph asset | `server/frontend/public/assets/operation-comparison/evonly_vmoderate_v2p90_pvess_multiseed.json` |

## 무거운 학습 경로

전체 재학습은 가볍지 않다.

1. station별 lower PI-SAC 300k step 학습.
2. Shared upper PI-SAC 15k step 학습.
3. corrected tariff evaluation.
4. five-method comparison.

팀원에게 처음부터 전체 재학습을 맡기기보다는, 먼저 artifact 확인과
평가표 재생성을 맡기는 편이 안전하다.

재학습/평가 스크립트 위치:

| 목적 | 스크립트 |
|---|---|
| lower PI-SAC 학습 | `ai_module/scripts/paper_repro/train_sharing_arm.py` |
| shared upper 학습/평가 | `ai_module/scripts/paper_repro/train_eval_shared_pisac.py` |
| corrected tariff 평가 | `ai_module/scripts/paper_repro/eval_contract_guarded_sharing.py` |
| 5-method 비교 | `ai_module/scripts/paper_repro/compare_five_methods_asym525.py` |
