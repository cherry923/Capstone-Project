# AI Lab Data Map

이 폴더는 큰 CSV를 직접 보관하지 않는다. `ai` 레포를 무겁게 만들지 않기
위해 실험 입력 데이터는 workspace root의 `data/`와 `ai_module/artifacts/`를
참조한다.

팀원이 데이터를 확인할 때는 프로젝트 루트에서 아래 경로를 보면 된다.

## Main Scenario

| 구분 | 경로 |
|---|---|
| 최종 프론트/보고서 train CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_train.csv` |
| 최종 프론트/보고서 test CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_test.csv` |
| 이전 accepted headline train CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evfcst_v1_train.csv` |
| 이전 accepted headline test CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evfcst_v1_test.csv` |
| EV v3 후보 train CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evfcst_v3_p90winsor_train.csv` |
| EV v3 후보 test CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evfcst_v3_p90winsor_test.csv` |
| EV Transformer 후보 train CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v1_train.csv` |
| EV Transformer 후보 test CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v1_test.csv` |
| EV Transformer shape-cal 후보 train CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v1_shapecal_train.csv` |
| EV Transformer shape-cal 후보 test CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v1_shapecal_test.csv` |
| EV Transformer v2 p90 EV-only volume-moderate train CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_train.csv` |
| EV Transformer v2 p90 EV-only volume-moderate test CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_evonly_volume_moderate_test.csv` |
| sharealign 민감도 train CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_sharealign_v1_pvfcst_tree_v5_evfcst_v1_train.csv` |
| sharealign 민감도 test CSV | `data/processed/ev/sharing_3arm/multi_pv6000_shift048_sharealign_v1_pvfcst_tree_v5_evfcst_v1_test.csv` |

## Raw / Processed Sources

| 구분 | 경로 | 설명 |
|---|---|---|
| KEPCO 시설유형 EV | `data/processed/ev/kepco_facility_hourly_20260520/kepco_facility_2020_2022_facility_group_hourly.csv` | 메인 3-station EV 수요의 기반 |
| KEPCO 지역+시설유형 EV | `data/processed/ev/kepco_facility_hourly_20260520/kepco_facility_2020_2022_region_facility_group_hourly_sparse.csv` | 제주 subset 검토 가능 |
| 제주 EV 전체 수요 | `data/processed/ev/hourly/jeju_ev_total_hourly_clean.csv` | 지역 일관성은 좋지만 시설유형 없음 |
| 제주 EV 상위 50 station | `data/processed/ev/hourly/jeju_ev_station_hourly_top50.csv` | 제주 station 기반 재구성 후보 |
| 제주 PV/날씨 | `data/processed/pv/site_actual/pv_actual_2018_2023_hourly.csv` | PV tree/TFT 후보 입력 |

## Metadata

| 구분 | 경로 |
|---|---|
| 최종 보고서용 PV/EV 예측 결과 요약 (AI 레포 포함) | `ai/ai_labs/data/final_forecast_contract.json` |
| 최종 PV tree + EV Transformer v2 p90 metadata | `ai_module/artifacts/sharing_3arm/forecast_observation/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90.json` |
| 이전 PV tree + EV v1 metadata | `ai_module/artifacts/sharing_3arm/forecast_observation/multi_pv6000_shift048_pvfcst_tree_v5_evfcst_v1.json` |
| EV v3 metadata | `ai_module/artifacts/sharing_3arm/forecast_observation/multi_pv6000_shift048_evfcst_v3_p90winsor.json` |
| PV tree + EV v3 metadata | `ai_module/artifacts/sharing_3arm/forecast_observation/multi_pv6000_shift048_pvfcst_tree_v5_evfcst_v3_p90winsor.json` |
| EV Transformer metadata | `ai_module/artifacts/sharing_3arm/forecast_observation/multi_pv6000_shift048_evtfm_v1.json` |
| PV tree + EV Transformer metadata | `ai_module/artifacts/sharing_3arm/forecast_observation/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v1.json` |
| EV Transformer model | `ai_module/artifacts/sharing_3arm/forecast_observation/evtfm_v1_model/ev_shape_transformer.pt` |
| PV tree + EV Transformer shape-cal metadata | `ai_module/artifacts/sharing_3arm/forecast_observation/multi_pv6000_shift048_pvfcst_tree_v5_evtfm_v1_shapecal.json` |

## Related Result Artifacts

| 구분 | 경로 |
|---|---|
| EV Transformer shape-cal full retrain corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_evtfm_v1_shapecal_fullretrain_tariff8320_seed1.json` |
| EV Transformer shape-cal full retrain 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_shapecal_fullretrain_tariff8320_seed1_aligned_oracle.json` |
| EV Transformer shape-cal 3-seed corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_evtfm_v1_shapecal_multiseed_tariff8320_seed1_2_42.json` |
| EV Transformer shape-cal 3-seed 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_shapecal_multiseed_tariff8320_seed1_2_42_aligned_oracle.json` |
| EV Transformer shape-cal lookahead local-only sensitivity | `ai_module/artifacts/sharing_3arm/forecast_observation/local_only_pvfcst_tree_v5_evtfm_v1_shapecal_fcstlookahead_multiseed_tariff8320_seed1_2_42.json` |
| EV Transformer shape-cal lookahead 3-seed corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_evtfm_v1_shapecal_fcstlookahead_multiseed_tariff8320_seed1_2_42.json` |
| EV Transformer shape-cal lookahead 3-seed 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_shapecal_fcstlookahead_multiseed_tariff8320_seed1_2_42_aligned_oracle.json` |
| EV Transformer share-aware lower seed1 corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_evtfm_v1_shapecal_fcstlookahead_shareaware_softmilp_seed1_tariff8320.json` |
| EV Transformer share-aware lower seed1 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_shapecal_fcstlookahead_shareaware_softmilp_seed1_tariff8320_aligned_oracle.json` |
| EV Transformer mixed share-aware lower seed1 corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_evtfm_v1_shapecal_fcstlookahead_shareaware_mixsoftzero035_seed1_tariff8320.json` |
| EV Transformer mixed share-aware lower seed1 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_shapecal_fcstlookahead_shareaware_mixsoftzero035_seed1_tariff8320_aligned_oracle.json` |
| EV Transformer mixed share-aware lower 3-seed corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_evtfm_v1_shapecal_fcstlookahead_shareaware_mixsoftzero035_multiseed_tariff8320_seed1_2_42.json` |
| EV Transformer mixed share-aware lower 3-seed 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v1_shapecal_fcstlookahead_shareaware_mixsoftzero035_multiseed_tariff8320_seed1_2_42_aligned_oracle.json` |
| EV Transformer v2 p90 peakrisk seed1 corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_peakqueuefcst_seed1_tariff8320.json` |
| EV Transformer v2 p90 peakrisk seed1 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_peakqueuefcst_seed1_tariff8320_physical_oracle.json` |
| EV Transformer v2 p90 share-aware fine-tune zero-sum corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_shareawareft_seed1_tariff8320.json` |
| EV Transformer v2 p90 share-aware fine-tune zero-sum 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_shareawareft_seed1_tariff8320_physical_oracle.json` |
| EV Transformer v2 p90 share-aware fine-tune pv_ess corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_shareawareft_pvess_seed1_tariff8320.json` |
| EV Transformer v2 p90 share-aware fine-tune pv_ess 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_shareawareft_pvess_seed1_tariff8320_physical_oracle.json` |
| EV Transformer v2 p90 share-aware fine-tune pv_only corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_shareawareft_pvonly_seed1_tariff8320.json` |
| EV Transformer v2 p90 share-aware fine-tune pv_only 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_evtfm_v2_peakaware_shapecal_p90_fcstpeakrisk_shareawareft_pvonly_seed1_tariff8320_physical_oracle.json` |
| Main physical P2P pv_ess corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_fcstpeakrisk_pvess_mtarget_multiseed_tariff8320_seed1_2_42.json` |
| Main physical P2P pv_ess 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_fcstpeakrisk_pvess_mtarget_multiseed_tariff8320_seed1_2_42_physical_oracle.json` |
| Main physical P2P pv_only corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_pvfcst_tree_v5_fcstpeakrisk_pvonly_mtarget_multiseed_tariff8320_seed1_2_42.json` |
| Main physical P2P pv_only 5-method | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_pvfcst_tree_v5_fcstpeakrisk_pvonly_mtarget_multiseed_tariff8320_seed1_2_42_physical_oracle.json` |
| EV-only volume-moderate physical P2P corrected tariff | `ai_module/artifacts/sharing_3arm/forecast_observation/corrected_tariff_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42.json` |
| EV-only volume-moderate physical P2P 5-method with grid-only/passive-PV split | `ai_module/artifacts/sharing_3arm/forecast_observation/five_method_comparison_evonly_vmoderate_v2p90_fcstpeakrisk_pvess_multiseed_tariff8320_seed1_2_42_physical_oracle.json` |

## Rule

- 큰 원본 CSV, `.pt`, 학습 로그는 이 폴더로 복사하지 않는다.
- `final_forecast_contract.json`은 팀원이 `ai` 레포만 받아도 보고서용 PV/EV 모델명,
  기간, 오차율, 원본 결과 경로를 확인할 수 있게 둔 작은 요약 파일이다.
- 새 데이터셋을 만들면 여기에 경로와 용도를 추가한다.
- 발표/문서에 쓰는 그림은 `ai_labs/results/README.md`에서 추적한다.
