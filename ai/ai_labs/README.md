# AI Experiment Lab

이 폴더는 팀원이 AI 실험을 따라가거나 결과를 다시 확인할 수 있게 만든
실험실 입구다.

중요한 구분부터 잡고 가야 한다.

| 위치 | 역할 |
|---|---|
| `ai/` | 팀원이 clone해서 실행할 AI API 서버 레포 |
| `ai_module/` | 예측/의사결정 오프라인 실험 스크립트와 artifact |
| `data/` | 원본/처리된 PV, EV, sharing scenario CSV |
| `ai_module/artifacts/` | 모델 평가 결과, 비교표, 그래프, 학습 산출물 |

현재 성능표와 실험 히스토리는 server API를 호출해서 만든 것이 아니다.
대부분 `ai_module`의 Python 스크립트가 CSV를 읽고 학습/평가한
오프라인 실험 결과다. `ai/` 서버는 이 결과를 API로 감싸거나 데모 응답을
내보내는 역할에 가깝다.

## 문서 구성

| 문서 | 내용 |
|---|---|
| [docs/data_and_forecasts.md](docs/data_and_forecasts.md) | PV/EV 데이터, 예측값/실제값, 모델 성능 |
| [docs/decision_experiments.md](docs/decision_experiments.md) | 하위/상위 의사결정 모델, 5-method 비교 |
| [docs/result_history.md](docs/result_history.md) | 지금까지 완료된 주요 실험 히스토리 |
| [docs/teammate_runbook.md](docs/teammate_runbook.md) | 팀원이 확인/재현할 때 쓰는 실행 순서 |
| [data/README.md](data/README.md) | 실험 입력 데이터와 scenario CSV 위치 |
| [results/README.md](results/README.md) | 주요 결과 artifact와 해석 기준 |

## 빠른 상태 확인

프로젝트 루트에서 실행한다.

```bash
cd <workspace-root>
python3 ai/ai_labs/scripts/check_experiment_artifacts.py
```

필수 artifact가 없으면 경고가 뜬다. CI나 commit 전 점검처럼 쓰려면
`--strict`를 붙인다.

```bash
python3 ai/ai_labs/scripts/check_experiment_artifacts.py --strict
```

## 현재 프론트/제출 보고서 기준 결과

프론트의 "Decision Model Comparison" 그래프와 제출 보고서용 비교표는
다음 구성을 기준으로 한다. `ai/` 서버의 PV 예측 API는 Han TFT 패키지를
로드할 수 있지만, 이 최종 비교 수치는 `ai_module`에서 생성한 offline
실험 artifact를 사용한다.

| 파트 | 현재 기준 |
|---|---|
| PV 예측 | tree 기반 회귀 모델 `tree_v5_hgb_absolute_error` |
| EV 예측 | EV Transformer v2 peak-aware shape-calibrated p90 |
| 시나리오 | EV-only volume-moderate physical P2P |
| 하위 의사결정 | station별 PI-SAC lower |
| 상위 의사결정 | Shared PI-SAC upper |
| 평가 기간 | 2022-01-01 ~ 2022-02-28 |
| seed | 1, 2, 42 평균 |
| 핵심 비교 | Grid-only, Passive-PV, Local ESS SAC, Shared PI-SAC, Forecast MILP, Hindsight MILP |

주요 source of truth:

| 항목 | 경로 |
|---|---|
| 최종 비교 CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_test.csv` |
| 최종 5-method artifact | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42_physical_oracle.json` |
| 프론트 graph asset | `server/frontend/public/assets/operation-comparison/evonly_vmoderate_v2p90_pvess_multiseed.json` |

핵심 수치:

| method | total@8320 M KRW | grid-only 대비 | passive-PV 대비 | local no-P2P 대비 |
|---|---:|---:|---:|---:|
| Grid-only default | 198.663 | +0.00% | +51.27% | +70.50% |
| Passive-PV default | 131.333 | -33.89% | +0.00% | +12.71% |
| Local ESS SAC (no P2P) | 116.520 | -41.35% | -11.28% | +0.00% |
| Forecast-based Shared PI-SAC | 110.703 | -44.28% | -15.71% | -4.99% |
| Forecast rolling MILP | 111.958 | -43.64% | -14.75% | -3.92% |
| Hindsight MILP upper bound | 95.559 | -51.90% | -27.24% | -17.99% |

해석은 이렇게 잡으면 된다.

- 논문식 grid-only 기준으로 보면 Shared PI-SAC는 `-44.28%`다. 이 값에는
  PV 사용 효과도 포함된다.
- 프론트 그래프와 보고서의 기본 비교 기준은 Passive-PV default다.
  이 기준으로 보면 Shared PI-SAC는 `-15.71%`다.
- local ESS만 쓰는 SAC 대비 P2P 공유를 추가한 순수 효과는 `-4.99%`다.

## 커밋 전 주의

- `ai_module`은 현재 별도 git repo가 아니다. 실험 스크립트와 artifact는
  이 workspace 안에 있지만 `ai` 레포 commit에는 직접 포함되지 않는다.
- 큰 학습 artifact나 `.pt` 파일을 `ai/`에 복사하지 않는다.
- 팀 공유 문서는 artifact 경로를 참조하고, 필요한 경우 작은 검증 스크립트만
  `ai/ai_labs/scripts/`에 둔다.
- `server/frontend` 변경은 이 실험실 정리와 별개다.
