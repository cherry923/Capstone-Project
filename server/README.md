# 다중 전기차 충전 관리 시스템

## 팀 실행 가이드

- 서버 + AI dispatch 연동 재현: `docs/TEAM_AI_DISPATCH_RUNBOOK.md`
- 프론트 1차 연동 규격: `docs/AI_프론트_의사결정_API_연동규격서.md`

test commit
## Backend

### 사용자 기능
- [ ] 로그인 API
- [ ] JWT 인증 구현
- [ ] 사용자 정보 조회

### 충전소 관리
- [ ] 충전소 등록 API
- [ ] 충전소 목록 조회 API
- [ ] 충전소 상세 조회 API

### 데이터 수집
- [ ] MQTT 메시지 수신
- [ ] 충전 데이터 저장
- [ ] ESS 상태 저장
- [ ] PV 발전량 저장

### 캐싱
- [ ] Redis 연결
- [ ] 실시간 충전 상태 캐싱
- [ ] ESS 상태 캐싱

### AI 연동
- [ ] FastAPI 서버 연동
- [ ] PV 예측 API 호출
- [ ] EV 수요 예측 API 호출

---

## AI Module

### 데이터 처리
- [ ] 데이터 전처리
- [ ] 학습 데이터 생성

### 예측 모델
- [ ] PV 발전량 예측 모델
- [ ] EV 충전 수요 예측 모델

### API
- [ ] FastAPI 서버 구축 //보류
- [ ] 예측 API 구현 //보류

---

## Frontend

- [ ] 로그인 페이지
- [ ] 충전소 지도 표시
- [ ] 충전소 상태 대시보드
- [ ] ESS 상태 그래프
- [ ] 발전량 그래프

---

## Infrastructure

- [ ] MySQL DB 구축
- [ ] Redis 구축
- [ ] MQTT Broker 구축
- [ ] Docker 환경 구축 //보류 
- [ ] AWS 배포// 보류
