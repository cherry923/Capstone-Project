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
        active: 0,
        total: 5,
        vehicles: 17,
        policy: "완속 충전기 2대 유지, 보조 배터리 충전 15kW",
        prediction: "다음 30분 수요 +12%",
        command: "대기 차량 우선순위 2단계 적용",
        connectors: [
            ["AC-01", "대기", "ready"],
            ["AC-02", "대기", "ready"],
            ["AC-03", "대기", "ready"],
            ["AC-04", "대기", "ready"],
            ["AC-05", "대기", "ready"]
        ]
    },
    {
        id: 2,
        name: "서울 마포 스테이션",
        region: "서울 마포구",
        status: "주의",
        demand: 164,
        ess: 48,
        renewable: 76,
        pvForecast: [76, 94, 101, 82],
        tariff: 132,
        active: 1,
        total: 3,
        vehicles: 11,
        policy: "보조 배터리 사용 20kW, 인근 충전소 전력 지원 요청",
        prediction: "결제 대기 증가 예상",
        command: "급속 충전 출력 5% 하향",
        connectors: [
            ["AC-01", "사용 가능", "ready"],
            ["AC-02", "충전 중", "150kW"],
            ["AC-03", "통신 지연", "warning"]
        ]
    },
    {
        id: 3,
        name: "서울 송파 에너지 파크",
        region: "서울 송파구",
        status: "정상",
        demand: 121,
        ess: 82,
        renewable: 58,
        pvForecast: [58, 72, 86, 69],
        tariff: 96,
        active: 1,
        total: 3,
        vehicles: 8,
        policy: "남는 태양광 전력 저장 유지",
        prediction: "피크 전 20분 여유",
        command: "추가 조치 없음",
        connectors: [
            ["AC-01", "충전 중", "120kW"],
            ["AC-03", "사용 가능", "ready"],
            ["AC-04", "사용 가능", "ready"]
        ]
    }
];
const stationPortCapacity = {
    "1": 5,
    "2": 3,
    "3": 3
};
const params = new URLSearchParams(window.location.search);
const stationId = Number(params.get("id")) || 1;
let station = stations.find((item) => item.id === stationId) || stations[0];
function inferDefaultApiBase() {
    const localHosts = ["localhost", "127.0.0.1", "::1"];
    const staticFrontendPorts = ["3000", "4173", "4177", "5500"];
    const isLocalStaticFrontend = localHosts.includes(window.location.hostname) &&
        staticFrontendPorts.includes(window.location.port);
    if (window.location.protocol === "file:" || isLocalStaticFrontend) {
        return "http://127.0.0.1:8080";
    }
    return "";
}
const defaultApiBase = inferDefaultApiBase();
const apiBase = (params.get("api") ||
    window.localStorage.getItem("gridflowApiBase") ||
    defaultApiBase).replace(/\/$/, "");
const defaultTimelapsePeriodKey = "presentation-2022-feb-transformer-month-loop";
const allowedTimelapsePeriodKeys = new Set([
    defaultTimelapsePeriodKey,
    "presentation-2022-jan-feb-transformer-lookahead"
]);
const isReplayDetail = params.get("view") === "replay" || params.has("period") || params.has("frame");
const stationHero = document.getElementById("station-hero");
const stationDetailPage = document.getElementById("station-detail-page");
const stationPolicyPage = document.getElementById("station-policy-page");
const backLink = document.querySelector(".back-link");
const chargerMeasurementsPath = "/api/v1/chargers/measurements";
const timelapsePeriodsPath = "/api/v1/ai/timelapse-periods";
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
function normalizeTimelapsePeriodKey(periodKey) {
    const normalized = (periodKey || "").trim();
    return allowedTimelapsePeriodKeys.has(normalized) ? normalized : defaultTimelapsePeriodKey;
}
function formatTimelineDate(value) {
    if (!value)
        return "";
    const text = String(value);
    const match = text.match(/(\d{4})-(\d{2})-(\d{2})/);
    if (!match)
        return text;
    return `${Number(match[2])}월 ${Number(match[3])}일`;
}
function replayDemandStatus(demand, active, total, ess) {
    const useRate = total ? active / total : 0;
    if (ess < 45)
        return "주의";
    if (demand >= 550 || useRate >= 0.9)
        return "혼잡";
    return "정상";
}
function normalizeReplayStatus(rawStatus, fallbackStatus) {
    const status = String(rawStatus || "").trim();
    if (status.includes("혼잡"))
        return "혼잡";
    if (status.includes("주의"))
        return "주의";
    if (status.includes("정상") || status.includes("보통") || status.includes("여유"))
        return "정상";
    return fallbackStatus;
}
function replayShareLabel(amount) {
    if (amount > 0)
        return `전력 ${amount.toFixed(1)}kWh 수신`;
    if (amount < 0)
        return `전력 ${Math.abs(amount).toFixed(1)}kWh 송신`;
    return "전력 공유 없음";
}
function replayCommandLabel(amount) {
    if (amount > 0)
        return "공유 전력 수신, ESS 방전 완화";
    if (amount < 0)
        return "잉여 전력 공유, ESS 충전 유지";
    return "충전소 자체 운영 유지";
}
function buildReplayConnectors(total, active, demand) {
    const safeTotal = Math.max(0, Math.round(Number(total || 0)));
    const safeActive = Math.min(Math.max(0, Math.round(Number(active || 0))), safeTotal);
    const powerPerActive = safeActive > 0 ? Math.max(1, Math.round(Number(demand || 0) / safeActive)) : 0;
    return Array.from({ length: safeTotal }, (_, index) => {
        const chargerLabel = `AC-${String(index + 1).padStart(2, "0")}`;
        const charging = index < safeActive;
        return [
            chargerLabel,
            charging ? "충전 중" : "대기",
            charging ? `${powerPerActive}kW` : "ready"
        ];
    });
}
function normalizeReplayStationFrame(frame) {
    if (!frame)
        return null;
    const rawTotal = Number(frame.total_chargers ?? frame.totalChargers ?? frame.total ?? station.total);
    const total = stationPortCapacity[String(station.id)] ?? (Number.isFinite(rawTotal) ? rawTotal : station.total);
    const rawActive = Number(frame.active_chargers ?? frame.activeChargers ?? frame.active ?? station.active);
    const active = Math.min(Math.max(Number.isFinite(rawActive) ? rawActive : station.active, 0), total);
    const demand = Math.round(Number(frame.demand_kwh ?? frame.demandKwh ?? frame.demand ?? station.demand));
    const renewable = Math.round(Number(frame.pv_kw ?? frame.pvKw ?? frame.renewable ?? station.renewable));
    const ess = Math.round(Number(frame.ess_percent ?? frame.essPercent ?? frame.ess ?? station.ess));
    const tariff = Math.round(Number(frame.tariff_krw_per_kwh ?? frame.tariffKrwPerKwh ?? frame.tariff ?? station.tariff));
    const shareEnergyKwh = Number(frame.share_energy_kwh ?? frame.shareEnergyKwh ?? 0);
    return {
        stationName: frame.station_name ?? frame.stationName,
        region: frame.region,
        demand,
        renewable,
        ess,
        tariff,
        active,
        total,
        vehicles: frame.vehicle_count ?? frame.vehicleCount ?? station.vehicles,
        shareEnergyKwh,
        status: frame.status,
        command: frame.command_text ?? frame.command,
        policy: frame.policy_text ?? frame.policy,
        prediction: frame.prediction_text ?? frame.prediction
    };
}
function applyReplayStationFrame(frame, periodFrame, periodLabel) {
    const normalized = normalizeReplayStationFrame(frame);
    if (!normalized)
        return false;
    const shareLabel = replayShareLabel(normalized.shareEnergyKwh);
    const hour = Number(periodFrame.hour);
    const timeLabel = `${formatTimelineDate(periodFrame.date)} ${String(Number.isFinite(hour) ? hour : 0).padStart(2, "0")}시`;
    station = {
        ...station,
        name: normalized.stationName || station.name,
        region: normalized.region || station.region,
        status: normalizeReplayStatus(normalized.status, replayDemandStatus(normalized.demand, normalized.active, normalized.total, normalized.ess)),
        demand: normalized.demand,
        ess: normalized.ess,
        renewable: normalized.renewable,
        pvForecast: [normalized.renewable, normalized.renewable, normalized.renewable, normalized.renewable],
        tariff: normalized.tariff,
        active: normalized.active,
        total: normalized.total,
        vehicles: normalized.vehicles,
        connectors: buildReplayConnectors(normalized.total, normalized.active, normalized.demand),
        command: normalized.command || replayCommandLabel(normalized.shareEnergyKwh),
        policy: normalized.policy || `${timeLabel} 리플레이 frame 기준 · ${shareLabel}`,
        prediction: normalized.prediction || `${periodLabel || "운영 리플레이"} 동기화 상태`
    };
    return true;
}
function configureBackLink() {
    if (!backLink)
        return;
    if (!isReplayDetail)
        return;
    const periodKey = normalizeTimelapsePeriodKey(params.get("period"));
    const frame = Number.isFinite(Number(params.get("frame"))) ? String(Math.max(0, Math.round(Number(params.get("frame"))))) : "624";
    const url = new URL("dashboard.html", window.location.href);
    url.searchParams.set("view", "replay");
    url.searchParams.set("period", periodKey);
    url.searchParams.set("frame", frame);
    url.searchParams.set("autoplay", params.get("autoplay") || "1");
    if (params.has("api")) {
        url.searchParams.set("api", params.get("api"));
    }
    backLink.setAttribute("href", url.href);
}
function normalizeEssRemain(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue))
        return null;
    return numericValue <= 1 ? numericValue * 100 : numericValue;
}
function stationNumberFromStationId(stationId) {
    const normalizedStationId = String(stationId ?? "").trim();
    const exactStation = stations.find((item) => String(item.id) === normalizedStationId);
    if (exactStation)
        return exactStation.id;
    const match = normalizedStationId.match(/\d+$/) || normalizedStationId.match(/\d+/);
    return match ? Number(match[0]) : null;
}
function applyChargerMeasurements(measurements) {
    const stationMeasurements = measurements
        .filter((measurement) => stationNumberFromStationId(measurement.stationId) === station.id)
        .sort((a, b) => Number(a.chargerNo || 0) - Number(b.chargerNo || 0));
    if (!stationMeasurements.length)
        return;
    const totalPower = stationMeasurements.reduce((sum, item) => sum + Number(item.power || 0), 0);
    const activeCount = stationMeasurements.filter((item) => item.charging === true).length;
    const latestEss = stationMeasurements
        .map((item) => normalizeEssRemain(item.essRemain))
        .filter((value) => value !== null)
        .at(-1);
    station = {
        ...station,
        demand: Math.round(totalPower),
        active: activeCount,
        total: stationMeasurements.length,
        connectors: stationMeasurements.map((measurement) => {
            const chargerLabel = `AC-${String(measurement.chargerNo).padStart(2, "0")}`;
            const connectorStatus = measurement.charging ? "충전 중" : "대기";
            const powerLabel = measurement.power != null && measurement.power > 0
                ? `${measurement.power}kW`
                : "ready";
            return [chargerLabel, connectorStatus, powerLabel];
        })
    };
    if (latestEss !== null && latestEss !== undefined) {
        station.ess = Math.round(latestEss);
    }
    if (station.ess < 45) {
        station.status = "주의";
    }
    else if (totalPower > 250) {
        station.status = "혼잡";
    }
    else {
        station.status = "정상";
    }
}
async function loadLatestMeasurements() {
    try {
        const response = await fetch(`${apiBase}${chargerMeasurementsPath}/latest-snapshot`);
        if (!response.ok)
            return;
        const body = await response.json();
        const measurements = Array.isArray(body) ? body : Array.isArray(body?.data) ? body.data : [];
        applyChargerMeasurements(measurements);
        renderStationDetail();
    }
    catch (error) {
        console.warn("Latest charger measurements fetch failed; using fallback station detail.", error);
    }
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
        prediction: run.model_status ? "AI 추천 운영 결과 반영" : "추천 계산 대기"
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
async function loadReplayStationDetail() {
    try {
        const periodKey = normalizeTimelapsePeriodKey(params.get("period"));
        const response = await fetch(`${apiBase}${timelapsePeriodsPath}/${encodeURIComponent(periodKey)}`);
        if (!response.ok)
            return;
        const body = await response.json();
        const detail = body?.data || body;
        const frames = Array.isArray(detail?.frames) ? detail.frames : [];
        if (!frames.length)
            return;
        const normalizedFrames = frames
            .map((periodFrame, ordinal) => {
            const frameIndex = Number(periodFrame.frame_index ?? periodFrame.frameIndex ?? ordinal);
            return {
                sortIndex: Number.isFinite(frameIndex) ? frameIndex : ordinal,
                date: periodFrame.frame_date ?? periodFrame.frameDate,
                hour: Number(periodFrame.hour),
                stations: Array.isArray(periodFrame.stations) ? periodFrame.stations : []
            };
        })
            .sort((left, right) => left.sortIndex - right.sortIndex);
        const requestedFrame = Number(params.get("frame"));
        const periodFrame = Number.isInteger(requestedFrame) && requestedFrame >= 0 && requestedFrame < normalizedFrames.length
            ? normalizedFrames[requestedFrame]
            : normalizedFrames.find((frame) => frame.sortIndex === requestedFrame) || normalizedFrames[0];
        const stationFrame = periodFrame.stations.find((item) => String(item.station_id ?? item.stationId) === String(station.id));
        if (applyReplayStationFrame(stationFrame, periodFrame, detail.label)) {
            renderStationDetail();
        }
    }
    catch (error) {
        console.warn("Replay station detail fetch failed; using fallback station detail.", error);
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
configureBackLink();
renderStationDetail();
if (isReplayDetail) {
    loadReplayStationDetail();
}
else {
    loadLatestDispatch().finally(loadLatestMeasurements);
    setInterval(loadLatestMeasurements, 5000);
}
