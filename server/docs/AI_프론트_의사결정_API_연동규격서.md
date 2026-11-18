# AI 의사결정 결과 프론트 연동 규격서

Document Version: v1.0.0
API Base Path: /api/v1/ai
작성 기준: 2026-05-12
대상 화면: 다중 충전소 운영 대시보드, 충전소 상세 화면

## 0. 공통 조회 응답 규격

프론트 조회 API는 기존 AI 모듈 API와 동일하게 최상위 공통 응답 형식을 사용한다. 백엔드 서버가 저장한 AI 의사결정 실행 결과는 `data` 내부에 넣고, `request_id`, `code`, `message`, `model_version`을 최상위에 둔다. 단, 프론트가 조회 요청을 보낼 때 `request_id`를 직접 생성하거나 전달할 필요는 없다.

```json
{
  "request_id": "req-20260512-0001",
  "code": "SUCCESS",
  "message": "요청이 정상적으로 처리되었습니다.",
  "model_version": "dispatch-flow-v1",
  "data": {}
}
```

필드명 | 타입 | 설명
---|---|---
`request_id` | string / null | 응답이 가리키는 추적용 식별자. 최신/상세 조회는 조회된 AI 실행 run의 request_id, 목록 조회는 null 또는 생략 가능
`code` | string | 처리 결과 코드. 정상 조회는 `SUCCESS`
`message` | string | 처리 결과 설명 메시지
`model_version` | string / null | 해당 실행에 사용된 모델 또는 정책 버전. 목록 조회는 null 가능
`data` | object / array / null | 실제 조회 결과. 최신/상세 조회는 실행 상세 object, 목록 조회는 summary array

공통 정책: 정상 조회는 HTTP 200으로 반환한다. 조회할 실행 결과가 없거나 특정 `runId`가 존재하지 않으면 HTTP 404가 가능하다. 운영 환경에서는 인증 실패 시 HTTP 401 또는 403을 반환한다.

## 1. 연동 범위 판단

현재 프론트가 해야 할 일이 "가장 최근에 실행된 AI 의사결정 결과를 화면에 표시"하는 것이라면 API는 1개만 있어도 된다.

필수 API:

```http
GET /api/v1/ai/dispatch-runs/latest
```

이 API 하나로 대시보드 요약, 충전소별 상태, 시간대별 PV 예측, ESS 제어 명령, 공유 전력량을 모두 표시할 수 있다. 현재 프론트 구현도 대시보드와 상세 화면 모두 이 API만 호출한다.

다만 다음 기능까지 프론트가 맡는다면 API가 추가로 필요하다.

| 기능 | 필요 API | 비고 |
|---|---|---|
| 최신 AI 결과 표시 | `GET /api/v1/ai/dispatch-runs/latest` | 필수 |
| 과거 실행 이력 목록 표시 | `GET /api/v1/ai/dispatch-runs?limit=20` | 선택 |
| 특정 실행 결과 다시 보기 | `GET /api/v1/ai/dispatch-runs/{runId}` | 선택 |
| 프론트에서 AI 실행 버튼 제공 | `POST /api/v1/ai/dispatch-24h` | 선택, 운영 권한 필요 |

따라서 프론트 연동 1차 범위는 `GET /api/v1/ai/dispatch-runs/latest` 하나로 고정하는 것이 가장 단순하다. `POST /dispatch-24h`는 백엔드, 관리자 배치, 또는 테스트 도구가 호출하고 프론트는 저장된 최신 결과만 읽는 구조가 안전하다.

## 2. 공통 조건

로컬 개발 Base URL 예시:

```text
http://127.0.0.1:8081
```

정적 HTML 테스트 시에는 URL query로 API 서버를 지정할 수 있다.

```text
dashboard.html?api=http://127.0.0.1:8081
station-detail.html?id=1&api=http://127.0.0.1:8081
```

데모 공개 실행 조건:

```text
AI_DISPATCH_DEMO_OPEN_ENABLED=true
FRONTEND_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500
```

운영 환경에서는 `AI_DISPATCH_DEMO_OPEN_ENABLED=false`를 기본으로 두고 인증된 사용자만 조회하도록 해야 한다.

### 2.1 request_id 결정 기준

`request_id`는 화면 표시용 입력값이 아니라 로그 추적과 실행 결과 연결을 위한 식별자이다. 따라서 프론트 조회 화면은 `request_id`를 만들지 않는다.

| API | 프론트 요청에서 request_id 필요 여부 | 응답 최상위 request_id 기준 |
|---|---:|---|
| `GET /api/v1/ai/dispatch-runs/latest` | 불필요 | 조회된 최신 AI 실행 run의 `request_id` |
| `GET /api/v1/ai/dispatch-runs/{runId}` | 불필요 | 조회된 특정 AI 실행 run의 `request_id` |
| `GET /api/v1/ai/dispatch-runs?limit=20` | 불필요 | 여러 run을 반환하므로 null 또는 생략 가능. 각 항목의 `data[*].request_id`를 사용 |
| `POST /api/v1/ai/dispatch-24h` | 선택 API | 호출 주체가 정한다. 프론트가 직접 실행 버튼을 만들지 않는 1차 범위에서는 백엔드/배치/관리자 도구가 생성 |

프론트에서 AI 실행 버튼을 제공하는 범위로 확장하더라도, 프론트가 임의 문자열을 만드는 방식보다는 백엔드가 UUID 또는 `dispatch-YYYYMMDD-*` 형태로 발급하는 방식이 더 안전하다. 팀에서 별도로 "클라이언트가 request_id를 넣는다"고 합의하지 않는 한, 프론트는 조회 API에 request_id를 보내지 않는다.

## 3. 최신 의사결정 결과 조회

### 3.1 요청

```http
GET /api/v1/ai/dispatch-runs/latest
Accept: application/json
```

요청 body는 없다.

### 3.2 응답 구조

```json
{
  "request_id": "smoke-20260512-135957",
  "code": "SUCCESS",
  "message": "success",
  "model_version": "dispatch-flow-v1",
  "data": {
    "run": {
      "run_id": 4,
      "request_id": "smoke-20260512-135957",
      "target_date": "2026-05-12",
      "status": "SUCCESS",
      "message": "success",
      "model_name": "upper_lower_rule_fallback",
      "model_status": "FALLBACK_REQUESTED",
      "pv_source": "daylight_fallback",
      "ev_source": "/path/to/ev_payload.json",
      "team_model_source": "/path/to/team_model",
      "command_count": 72,
      "created_at": "2026-05-12T13:59:57.778827"
    },
    "commands": [
      {
        "command_index": 0,
        "hour": 0,
        "station_id": "1",
        "share_energy_kwh": -67.50678,
        "ess_action": -0.08,
        "pv_priority": 1.0,
        "soc_before": 0.55,
        "soc_after": 0.47,
        "grid_total_kwh": 0.0,
        "grid_cost": 0.0,
        "command": "discharge_ess:pv_to_ev_first",
        "command_payload": {
          "self_supply_kwh": 0.0,
          "loss_kwh": 0.0,
          "peak_violation": 0.0,
          "soc_violation": 0.0,
          "objective_reward": 0.0
        }
      }
    ],
    "request_payload": {
      "request_id": "smoke-20260512-135957",
      "target_date": "2026-05-12",
      "timezone": "Asia/Seoul"
    },
    "response_payload": {
      "code": "SUCCESS",
      "message": "success",
      "data": {
        "forecasts": {
          "tou_24h": [102.0, 102.0],
          "stations": [
            {
              "station_id": 1,
              "init_soc": 0.55,
              "pv_forecast_24h": [0.0, 0.0],
              "ev_demand_forecast_24h": [425.0, 421.0]
            }
          ]
        },
        "dispatch": {
          "commands": [],
          "summary": {}
        },
        "model": {}
      },
    }
  }
}
```

`data.response_payload.data.forecasts.stations[*].pv_forecast_24h`, `ev_demand_forecast_24h`, `tou_24h`는 24개 값을 기준으로 사용한다. `data.commands`는 `station_id`와 `hour`로 매칭한다. 현재 3개 충전소, 24시간 기준이면 `data.run.command_count=72`가 정상이다.

## 4. 프론트 화면 매핑

### 4.1 대시보드 요약

| 화면 항목 | 응답 필드 | 계산 방식 |
|---|---|---|
| 실시간 충전 요청량 | `data.response_payload.data.forecasts.stations[*].ev_demand_forecast_24h` | 현재 hour 값 합산 |
| ESS 총 잔량 | `data.commands[*].soc_after` | 현재 hour 또는 마지막 명령의 평균 SoC |
| 예측 PV 발전량 | `data.response_payload.data.forecasts.stations[*].pv_forecast_24h` | 현재 시각부터 4시간 합산 |
| 현재 전기요금 구간 | `data.response_payload.data.forecasts.tou_24h` | 현재 hour 요금으로 피크/보통 구분 |
| AI 정책 라벨 | `data.run.model_status`, `data.run.pv_source` | 예: `FALLBACK_REQUESTED · PV daylight_fallback` |

### 4.2 충전소 카드와 상세 화면

| 화면 항목 | 응답 필드 | 계산 방식 |
|---|---|---|
| 충전소 ID | `data.commands[*].station_id` | 문자열 비교 가능 |
| 충전 요청량 | `data.response_payload.data.forecasts.stations[*].ev_demand_forecast_24h[hour]` | kWh 단위 |
| ESS 저장량 | `data.commands[*].soc_after` 또는 forecast `init_soc` | 0~1 값을 %로 변환 |
| PV 예측 발전량 | `data.response_payload.data.forecasts.stations[*].pv_forecast_24h[hour]` | kW 또는 kWh 표기 정책은 화면에서 통일 |
| 공유 전력량 | `data.commands[*].share_energy_kwh` | 양수는 유입, 음수는 유출 |
| ESS 제어 | `data.commands[*].ess_action`, `data.commands[*].command` | `discharge_ess` 방전, `charge_ess` 충전 |
| PV 우선순위 | `data.commands[*].pv_priority`, `data.commands[*].command` | `pv_to_ev_first`, `pv_to_ess_first` 등 |

현재 API에는 충전소 이름, 지역명, 포트 수, 커넥터 상태 같은 정적 메타데이터가 없다. 프론트 1차 구현에서는 정적 매핑 테이블을 사용해도 된다. 다만 이 정보까지 백엔드에서 관리하려면 별도 충전소 메타 API가 필요하다.

## 5. 명령 값 해석

`command`는 콜론 앞뒤로 ESS 행동과 PV 우선순위를 담는다.

| 원시 값 | 표시 문구 |
|---|---|
| `discharge_ess` | ESS 방전 |
| `charge_ess` | ESS 충전 |
| 그 외 | ESS 유지 |
| `pv_to_ev_first` | PV→EV 우선 |
| `pv_to_ess_first` | PV→ESS 우선 |
| 그 외 | PV 우선순위 유지 |

`share_energy_kwh`는 충전소 간 공유 방향이다.

| 값 | 의미 |
|---|---|
| 양수 | 다른 충전소 또는 공유 풀에서 전력을 받음 |
| 음수 | 다른 충전소 또는 공유 풀로 전력을 보냄 |
| 0 | 공유 없음 |

## 6. 예외 처리

| 상황 | HTTP/응답 | 프론트 처리 |
|---|---|---|
| 아직 실행 결과 없음 | 404 가능 | "아직 AI 의사결정 결과 없음" 표시 |
| `code != SUCCESS` | 200 + 실패 상태 저장 가능 | `message`와 `data.run.message`를 함께 표시 |
| `data.commands`가 비어 있음 | 200 | 대시보드 값은 forecast만 표시, 명령 영역은 대기 상태 |
| `data.response_payload.data.forecasts` 누락 | 200 | 정적 fallback 또는 빈 상태 표시 |
| 인증 필요 | 401/403 | 로그인 또는 권한 안내 |

## 7. 현재 검증 결과

2026-05-12 로컬 검증 기준:

| 항목 | 결과 |
|---|---|
| `GET /api/v1/ai/dispatch-runs/latest` | HTTP 200 |
| `run.status` | `SUCCESS` |
| `command_count` | 72 |
| 대시보드 렌더링 | 최신 API 값 표시 확인 |
| 상세 화면 렌더링 | 충전소 1번 기준 API 값 표시 확인 |
| 현재 PV 출처 | `daylight_fallback` |
| 현재 모델 상태 | `FALLBACK_REQUESTED` |

주의할 점은 현재 화면 연동은 "API와 저장/조회 흐름이 붙는지"를 확인한 상태라는 것이다. `pv_source=daylight_fallback`, `model_status=FALLBACK_REQUESTED`이면 최종 PV 실모델 결과로 검증된 상태는 아니다. 교수님 또는 팀원에게 설명할 때는 "의사결정 출력 흐름은 연결됐고, 최종 실모델 교체와 예보 기반 PV 검증은 남아 있다"고 구분해야 한다.
