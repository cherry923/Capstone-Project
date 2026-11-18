# 팀 실행 가이드: 서버 + AI 최종 dispatch 연동

이 문서는 팀원이 `server`와 `ai` 레포를 clean clone한 뒤 최종 발표용 24시간 dispatch 결과를 재현하는 절차다.

## 레포 배치

두 레포를 같은 상위 폴더에 둔다.

```text
capstone_main/
  server/
  ai/
```

`ai_module`은 git 레포가 아니므로 팀 실행 기준에서 제외한다. EV 수요 payload는 이제 `ai/app/data/ev_hybrid_calendar_24h_blend_sac_payload.json`에 포함되어 있다.

## 현재 연결 구조

```text
frontend/public/dashboard.html
  -> GET server /api/v1/ai/dispatch-runs/latest
server
  -> POST ai /api/v1/ai/flow/dispatch-24h
  -> ai_dispatch_run, ai_dispatch_command 테이블에 결과 저장
ai
  -> PV 예측 + EV 수요 payload + MILP/PI-SAC 의사결정
```

대시보드는 직접 AI 서버를 호출하지 않는다. 서버가 AI 결과를 저장하고, 프론트는 서버의 최신 dispatch run을 읽는 구조다.

## 권장 로컬 실행

### 1. AI 서버 실행

```bash
cd /path/to/capstone_main/ai
/opt/homebrew/bin/python3.13 -m venv .venv313
. .venv313/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

AI 단독 smoke:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/ai/flow/dispatch-24h \
  -H "Content-Type: application/json" \
  -d '{"request_id":"team-ai-smoke","target_date":"2026-05-07","init_soc":[0.55,0.5,0.45]}'
```

성공 기준은 `code=SUCCESS`, `command_count=72`다.

### 2. 서버 환경변수 준비

```bash
cd /path/to/capstone_main/server
cp .env.example .env
```

최소 확인 항목:

```properties
DB_URL=jdbc:postgresql://localhost:5432/postgres
DB_USERNAME=postgres
DB_PASSWORD=your_password_here
AI_MODULE_URL=http://localhost:8000
AI_DISPATCH_DEMO_OPEN_ENABLED=true
```

`AI_DISPATCH_DEMO_OPEN_ENABLED=true`는 발표/로컬 확인용이다. 이 값이 `false`면 dispatch 실행과 최신 결과 조회 API가 인증에 막힐 수 있다.

### 3. 서버 실행

```bash
cd /path/to/capstone_main/server
./gradlew bootRun --args='--server.port=8081'
```

서버에서 AI dispatch 실행:

```bash
curl -X POST http://127.0.0.1:8081/api/v1/ai/dispatch-24h \
  -H "Content-Type: application/json" \
  -d '{"request_id":"team-server-smoke","target_date":"2026-05-07","init_soc":[0.55,0.5,0.45]}'
```

저장된 최신 결과 확인:

```bash
curl http://127.0.0.1:8081/api/v1/ai/dispatch-runs/latest
```

### 4. 프론트 확인

정적 프론트만 띄우려면:

```bash
cd /path/to/capstone_main/server/frontend/public
python3 -m http.server 4177 --bind 127.0.0.1
```

브라우저:

```text
http://127.0.0.1:4177/dashboard.html?api=http://127.0.0.1:8081
```

대시보드가 읽는 1차 API는 `GET /api/v1/ai/dispatch-runs/latest`다. 최신 run이 없으면 먼저 `POST /api/v1/ai/dispatch-24h`를 한 번 호출해야 한다.

## Docker Compose 실행

두 레포를 같은 상위 폴더에 둔 상태에서 서버 레포에서 실행한다.

```bash
cd /path/to/capstone_main/server
docker compose up --build
```

Compose는 다음을 함께 띄운다.

- `backend`: Spring 서버
- `ai`: sibling `../ai` 레포의 FastAPI 서버
- `postgres`: 로컬 PostgreSQL
- `redis`: Redis
- `mqtt`: Mosquitto

Compose 실행 시 서버는 `AI_MODULE_URL=http://ai:8000`으로 AI 컨테이너를 호출한다.

## EV payload는 historical scenario이다

`ai/app/data/ev_hybrid_calendar_24h_blend_sac_payload.json`은 `base_datetime = 2022-06-23 00:00:00` 기준의 고정 historical payload다. 발표 데모에서 `target_date=2026-05-07` 같은 미래 일자를 보내도 EV 수요 값 자체는 그 날짜에 대한 live forecast가 아니라 historical scenario다. 이 사실은 `data.warnings`와 `data.forecasts.source.ev_detail.target_date_mismatch_days`로 dispatch 응답에 명시되며, 서버의 `ai_dispatch_run.ev_source` 컬럼에도 그대로 저장된다.

발표 자료에는 다음과 같이 적는다.

```text
EV 수요 예측 모델은 2022-06-22까지의 제주 충전 이력 538일을 기준으로 학습·검증했다.
현재 dispatch API의 2026-05-07 날짜는 서버-프론트 연동과 의사결정 파이프라인을
검증하기 위한 요청 날짜이며, EV 수요 값 자체는 2022-06-23 00:00 기준 historical
scenario payload에서 제공된다. 본 발표의 성능 수치는 clean historical validation
기준이고, 2026년 실제 수요 예측 성능을 주장하지 않는다.
```

운영 적용 전 historical payload가 live 의사결정으로 흘러가는 것을 막으려면 AI 서버에 `EV_STRICT_TARGET_DATE=1`을 켠다. 기본은 strict OFF.

## 자주 막히는 지점

- `GET /api/v1/ai/dispatch-runs/latest`가 `403`이면 `AI_DISPATCH_DEMO_OPEN_ENABLED=true`가 적용되지 않은 것이다.
- AI 응답에 `EV SAC payload not found`가 나오면 `ai/app/data/ev_hybrid_calendar_24h_blend_sac_payload.json` 파일이 있는지 확인한다.
- 서버가 시작 중 DB에서 실패하면 `.env`의 `DB_URL`, `DB_USERNAME`, `DB_PASSWORD`가 실제 PostgreSQL과 맞는지 확인한다.
- 프론트는 AI 서버가 아니라 서버 API를 읽는다. 브라우저 URL의 `api=` 값은 `http://127.0.0.1:8081`처럼 서버 주소여야 한다.
- AI dispatch 응답의 `data.warnings`에 `historical payload` 메시지가 보이는 건 정상이다. 발표 안전 문구다.
