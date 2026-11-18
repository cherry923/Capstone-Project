const stations = [
    {
        id: 1,
        name: "서울 강남 허브",
        region: "서울 강남구",
        status: "정상",
        demand: 218,
        ess: 74,
        renewable: 92,
        pvForecast: [92, 118, 136, 104],
        tariff: 118,
        active: 10,
        total: 12,
        vehicles: 17,
        policy: "완속 충전기 2대 유지, 보조 배터리 충전 15kW",
        prediction: "다음 30분 수요 +12%",
        command: "대기 차량 우선순위 2단계 적용",
        connectors: [
            ["DC-01", "충전 중", "180kW"],
            ["DC-04", "충전 중", "160kW"],
            ["AC-02", "대기", "ready"]
        ]
    },
    {
        id: 2,
        name: "인천 물류 스테이션",
        region: "인천 연수구",
        status: "주의",
        demand: 164,
        ess: 48,
        renewable: 76,
        pvForecast: [76, 94, 101, 82],
        tariff: 132,
        active: 7,
        total: 9,
        vehicles: 11,
        policy: "보조 배터리 사용 20kW, 인근 충전소 전력 지원 요청",
        prediction: "결제 대기 증가 예상",
        command: "급속 충전 출력 5% 하향",
        connectors: [
            ["DC-02", "충전 중", "150kW"],
            ["DC-03", "통신 지연", "warning"],
            ["AC-01", "사용 가능", "ready"]
        ]
    },
    {
        id: 3,
        name: "대전 에너지 파크",
        region: "대전 유성구",
        status: "정상",
        demand: 121,
        ess: 82,
        renewable: 58,
        pvForecast: [58, 72, 86, 69],
        tariff: 96,
        active: 5,
        total: 8,
        vehicles: 8,
        policy: "남는 태양광 전력 저장 유지",
        prediction: "피크 전 20분 여유",
        command: "추가 조치 없음",
        connectors: [
            ["DC-01", "충전 중", "120kW"],
            ["AC-03", "사용 가능", "ready"],
            ["AC-04", "사용 가능", "ready"]
        ]
    }
];
const params = new URLSearchParams(window.location.search);
const stationId = Number(params.get("id")) || 1;
let station = stations.find((item) => item.id === stationId) || stations[0];
function inferDefaultApiBase() {
    const localHosts = ["localhost", "127.0.0.1", "::1"];
    const staticFrontendPorts = ["3000", "4173", "4177", "5500"];
    const isLocalStaticFrontend = localHosts.includes(window.location.hostname) &&
        staticFrontendPorts.includes(window.location.port);
    if (window.location.protocol === "file:" || isLocalStaticFrontend) {
        return "http://127.0.0.1:8081";
    }
    return "";
}
const defaultApiBase = inferDefaultApiBase();
const apiBase = (params.get("api") ||
    window.localStorage.getItem("gridflowApiBase") ||
    defaultApiBase).replace(/\/$/, "");
const stationHero = document.getElementById("station-hero");
const stationDetailPage = document.getElementById("station-detail-page");
const stationPolicyPage = document.getElementById("station-policy-page");
function stateClass(status) {
    if (status === "정상")
        return "ok";
    if (status === "주의")
        return "warn";
    return "alert";
}
function commandLabel(rawCommand) {
    if (!rawCommand)
        return "추천 조치 대기";
    const [ess = "", pv = ""] = String(rawCommand).split(":");
    const essLabel = ess.includes("discharge")
        ? "보조 배터리 사용"
        : ess.includes("charge")
            ? "보조 배터리 충전"
            : "보조 배터리 유지";
    const pvLabel = pv.includes("pv_to_ess")
        ? "태양광 전력을 배터리에 우선 저장"
        : pv.includes("pv_to_ev")
            ? "태양광 전력을 차량 충전에 우선 사용"
            : "태양광 사용 방식 유지";
    return `${essLabel}, ${pvLabel}`;
}
function currentHourIndex(length) {
    if (!length)
        return 0;
    return Math.min(new Date().getHours(), length - 1);
}
function applyDispatchDetail(detail) {
    const responseData = detail?.response_payload?.data;
    const forecastStations = responseData?.forecasts?.stations || [];
    const tou24h = responseData?.forecasts?.tou_24h || [];
    const commands = detail?.commands || [];
    const run = detail?.run || {};
    const forecast = forecastStations.find((item) => String(item.station_id) === String(station.id));
    const stationCommands = commands.filter((command) => String(command.station_id) === String(station.id));
    if (!forecast)
        return;
    const hour = currentHourIndex(tou24h.length || 24);
    const hourCommand = stationCommands.find((command) => Number(command.hour) === hour) || stationCommands[0] || {};
    const finalCommand = stationCommands.at(-1);
    const pv24h = forecast.pv_forecast_24h || [];
    const ev24h = forecast.ev_demand_forecast_24h || [];
    const pvWindow = [0, 1, 2, 3].map((offset) => Number(pv24h[(hour + offset) % pv24h.length] || 0));
    const finalSoc = Number(finalCommand?.soc_after ?? forecast.init_soc ?? station.ess / 100);
    station = {
        ...station,
        status: finalSoc < 0.32 ? "혼잡" : finalSoc < 0.45 ? "주의" : "정상",
        demand: Math.round(Number(ev24h[hour] || ev24h[0] || station.demand)),
        ess: Math.round(finalSoc * 100),
        renewable: Math.round(pvWindow[0] || Math.max(...pvWindow, 0)),
        pvForecast: pvWindow.map((value) => Math.round(value)),
        tariff: Math.round(Number(tou24h[hour] || station.tariff)),
        command: commandLabel(hourCommand.command),
        policy: `${commandLabel(hourCommand.command)} · 전력 이동 ${Number(hourCommand.share_energy_kwh || 0).toFixed(1)}kWh`,
        prediction: run.model_status ? `추천 계산 상태: ${run.model_status}` : "추천 계산 대기"
    };
}
async function loadLatestDispatch() {
    try {
        const response = await fetch(`${apiBase}/api/v1/ai/dispatch-runs/latest`);
        if (!response.ok)
            return;
        const body = await response.json();
        const detail = body?.data || body;
        applyDispatchDetail(detail);
        renderStationDetail();
    }
    catch (error) {
        console.warn("AI dispatch run fetch failed; using fallback station detail.", error);
    }
}
function renderStationDetail() {
    stationHero.innerHTML = `
  <div>
    <p class="eyebrow">충전소 상세</p>
    <h1>${station.name}</h1>
    <p>${station.region}의 충전 수요, 보조 배터리 잔량, 태양광 발전량, 전기요금과 권장 조치를 확인합니다.</p>
  </div>
  <span class="status-badge ${stateClass(station.status)}">${station.status}</span>
`;
    stationDetailPage.innerHTML = `
  <div class="detail-card">
    <div class="detail-tags">
      <span class="tag">충전 요청 ${station.demand}kWh</span>
      <span class="tag">충전 차량 ${station.vehicles}대</span>
      <span class="tag">사용 중 충전기 ${station.active}/${station.total}</span>
    </div>

    <div class="detail-grid">
      <div class="detail-row">
        <span>보조 배터리 잔량</span>
        <strong>${station.ess}%</strong>
      </div>
      <div class="detail-row">
        <span>태양광 발전량</span>
        <strong>${station.renewable}kW</strong>
      </div>
      <div class="detail-row">
        <span>전기요금</span>
        <strong>${station.tariff}원/kWh</strong>
      </div>
      <div class="detail-row">
        <span>권장 조치</span>
        <strong>${station.command}</strong>
      </div>
    </div>

    <div class="connector-list">
      ${station.connectors
        .map(([name, state, metric]) => `
            <div class="connector-item">
              <strong>${name}</strong>
              <span>${state}</span>
              <span class="meta">${metric}</span>
            </div>
          `)
        .join("")}
    </div>
  </div>
`;
    stationPolicyPage.innerHTML = `
  <article class="algo-card">
    <div class="algo-grid">
      <div class="algo-row">
        <span>현재 상황</span>
        <strong>충전 요청 ${station.demand}kWh / 배터리 ${station.ess}% / 태양광 ${station.renewable}kW</strong>
      </div>
      <div class="algo-row">
        <span>계산 상태</span>
        <strong>${station.prediction}</strong>
      </div>
      <div class="policy-box">
        <p class="eyebrow">권장 조치</p>
        <p>${station.policy}</p>
      </div>
    </div>
  </article>
`;
}
renderStationDetail();
loadLatestDispatch();
