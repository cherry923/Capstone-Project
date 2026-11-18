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
        pos: { x: 18, y: 18 },
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
        pos: { x: 63, y: 28 },
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
        pos: { x: 34, y: 58 },
        connectors: [
            ["DC-01", "충전 중", "120kW"],
            ["AC-03", "사용 가능", "ready"],
            ["AC-04", "사용 가능", "ready"]
        ]
    }
];
const filters = ["전체", "정상", "주의", "혼잡"];
let currentFilter = "전체";
let selectedStationId = 1;
let searchQuery = "";
const stationNodes = document.getElementById("station-nodes");
const stationList = document.getElementById("station-list");
const algoPanel = document.getElementById("algo-panel");
const tariffList = document.getElementById("tariff-list");
const costComparisonPanel = document.getElementById("cost-comparison-panel");
const statusFilters = document.getElementById("status-filters");
const searchInput = document.getElementById("search-input");
const themeSwitcher = document.getElementById("theme-switcher");
const settingsToggle = document.getElementById("settings-toggle");
const themePopover = document.getElementById("theme-popover");
const themeStorageKey = "gridflowThemeApp";
const savedTheme = window.localStorage.getItem(themeStorageKey) || "light";
document.body.dataset.theme = savedTheme;
function setupThemeControls() {
    if (!settingsToggle || !themePopover || !themeSwitcher)
        return;
    settingsToggle.addEventListener("click", (event) => {
        event.stopPropagation();
        const isOpen = !themePopover.hidden;
        themePopover.hidden = isOpen;
        settingsToggle.setAttribute("aria-expanded", String(!isOpen));
    });
    themeSwitcher.querySelectorAll(".theme-chip").forEach((button) => {
        button.classList.toggle("active", button.dataset.theme === savedTheme);
        button.addEventListener("click", () => {
            document.body.dataset.theme = button.dataset.theme;
            window.localStorage.setItem(themeStorageKey, button.dataset.theme);
            themeSwitcher
                .querySelectorAll(".theme-chip")
                .forEach((chip) => chip.classList.toggle("active", chip === button));
            themePopover.hidden = true;
            settingsToggle.setAttribute("aria-expanded", "false");
        });
    });
    document.addEventListener("click", (event) => {
        if (themePopover.hidden)
            return;
        const target = event.target;
        if (themePopover.contains(target) || settingsToggle.contains(target))
            return;
        themePopover.hidden = true;
        settingsToggle.setAttribute("aria-expanded", "false");
    });
}
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
const apiParams = new URLSearchParams(window.location.search);
const defaultApiBase = inferDefaultApiBase();
const apiBase = (apiParams.get("api") ||
    window.localStorage.getItem("gridflowApiBase") ||
    defaultApiBase).replace(/\/$/, "");
const chargerMeasurementsPath = "/api/chargers/measurements";
const metricUptime = document.getElementById("metric-uptime");
const metricDemand = document.getElementById("metric-demand");
const metricSavings = document.getElementById("metric-savings");
const summaryRequest = document.getElementById("summary-request");
const summaryEss = document.getElementById("summary-ess");
const summaryRenewable = document.getElementById("summary-renewable");
const summaryTariff = document.getElementById("summary-tariff");
const iotStatus = document.getElementById("iot-status");
const aiPolicyLabel = document.getElementById("ai-policy-label");
let liveDispatchLoaded = false;
let liveMeasurementsLoaded = false;
let latestTou24h = [];
const latestMeasurementsByCharger = new Map();
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
function stationStatusFrom(commands, station) {
    const latest = commands.at(-1);
    const peakGrid = Math.max(...commands.map((command) => Number(command.grid_total_kwh || 0)), 0);
    const finalSoc = Number(latest?.soc_after ?? station.ess / 100);
    if (finalSoc < 0.32 || peakGrid > 500)
        return "혼잡";
    if (finalSoc < 0.45 || peakGrid > 250)
        return "주의";
    return "정상";
}
function currentHourIndex(length) {
    if (!length)
        return 0;
    return Math.min(new Date().getHours(), length - 1);
}
function rotated24h(values, fallbackValue = 0) {
    const source = Array.isArray(values) ? values : [];
    const hour = currentHourIndex(source.length || 24);
    return Array.from({ length: 24 }, (_, index) => {
        if (!source.length)
            return fallbackValue;
        return Number(source[(hour + index) % source.length] || fallbackValue);
    });
}
function applyDispatchDetail(detail) {
    const responseData = detail?.response_payload?.data;
    const forecastStations = responseData?.forecasts?.stations || [];
    const tou24h = responseData?.forecasts?.tou_24h || [];
    const commands = detail?.commands || [];
    const run = detail?.run || {};
    if (!forecastStations.length)
        return;
    latestTou24h = rotated24h(tou24h, stations[0]?.tariff || 120);
    const commandsByStation = commands.reduce((groups, command) => {
        const key = String(command.station_id);
        groups[key] = groups[key] || [];
        groups[key].push(command);
        return groups;
    }, {});
    const hour = currentHourIndex(tou24h.length || 24);
    stations.forEach((station) => {
        const forecast = forecastStations.find((item) => String(item.station_id) === String(station.id));
        const stationCommands = commandsByStation[String(station.id)] || [];
        if (!forecast)
            return;
        const hourCommand = stationCommands.find((command) => Number(command.hour) === hour) || stationCommands[0] || {};
        const finalCommand = stationCommands.at(-1);
        const pv24h = forecast.pv_forecast_24h || [];
        const ev24h = forecast.ev_demand_forecast_24h || [];
        const pvWindow = [0, 1, 2, 3].map((offset) => Number(pv24h[(hour + offset) % pv24h.length] || 0));
        station.status = stationCommands.length ? stationStatusFrom(stationCommands, station) : station.status;
        station.demand = Math.round(Number(ev24h[hour] || ev24h[0] || station.demand));
        station.ess = Math.round(Number(finalCommand?.soc_after ?? forecast.init_soc ?? station.ess / 100) * 100);
        station.evDemand24h = rotated24h(ev24h, station.demand);
        station.pvForecast24h = rotated24h(pv24h, station.renewable);
        station.pvForecast = pvWindow.map((value) => Math.round(value));
        station.renewable = station.pvForecast[0] || Math.round(Math.max(...pvWindow, 0));
        station.tariff = Math.round(Number(tou24h[hour] || station.tariff));
        station.command = commandLabel(hourCommand.command);
        station.policy = `${station.command} · 전력 이동 ${Number(hourCommand.share_energy_kwh || 0).toFixed(1)}kWh`;
        station.prediction = run.model_status
            ? `추천 계산 상태: ${run.model_status}`
            : "추천 계산 대기";
    });
    liveDispatchLoaded = true;
}
async function loadLatestDispatch() {
    try {
        const response = await fetch(`${apiBase}/api/v1/ai/dispatch-runs/latest`);
        if (!response.ok)
            return;
        const body = await response.json();
        const detail = body?.data || body;
        applyDispatchDetail(detail);
        renderAll();
    }
    catch (error) {
        console.warn("AI dispatch run fetch failed; using fallback station data.", error);
    }
}
let lastMeasurementId = 0;
function asMeasurementList(body) {
    if (Array.isArray(body))
        return body;
    if (Array.isArray(body?.data))
        return body.data;
    return [];
}
function updateLastMeasurementId(measurements) {
    const maxId = Math.max(lastMeasurementId, ...measurements.map((item) => Number(item.id || 0)));
    if (Number.isFinite(maxId)) {
        lastMeasurementId = maxId;
    }
}
function normalizeEssRemain(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue))
        return null;
    return numericValue <= 1 ? numericValue * 100 : numericValue;
}
function measurementKey(measurement) {
    return `${measurement.stationId}:${measurement.chargerNo}`;
}
async function loadLatestMeasurements() {
    try {
        const response = await fetch(`${apiBase}${chargerMeasurementsPath}/latest-snapshot`);
        if (!response.ok) {
            throw new Error(`최신 스냅샷 조회 실패: ${response.status}`);
        }
        const data = asMeasurementList(await response.json());
        if (data.length === 0) {
            return;
        }
        applyChargerMeasurements(data);
        updateLastMeasurementId(data);
        liveMeasurementsLoaded = true;
        renderAll();
    }
    catch (error) {
        console.warn("최신 충전기 스냅샷 조회 실패", error);
    }
}
async function loadMeasurementChanges() {
    if (!lastMeasurementId) {
        await loadLatestMeasurements();
        return;
    }
    try {
        const response = await fetch(`${apiBase}${chargerMeasurementsPath}/changes?afterId=${encodeURIComponent(lastMeasurementId)}`);
        if (!response.ok) {
            throw new Error(`충전기 변경분 조회 실패: ${response.status}`);
        }
        const data = asMeasurementList(await response.json());
        if (data.length === 0)
            return;
        applyChargerMeasurements(data);
        updateLastMeasurementId(data);
        liveMeasurementsLoaded = true;
        renderAll();
    }
    catch (error) {
        console.warn("충전기 변경분 조회 실패", error);
    }
}
function stationNumberFromStationId(stationId) {
    const normalizedStationId = String(stationId ?? "").trim();
    const exactStation = stations.find((station) => String(station.id) === normalizedStationId);
    if (exactStation)
        return exactStation.id;
    const match = normalizedStationId.match(/\d+$/) || normalizedStationId.match(/\d+/);
    return match ? Number(match[0]) : null;
}
function applyChargerMeasurements(measurements) {
    measurements.forEach((measurement) => {
        if (measurement.stationId == null || measurement.chargerNo == null)
            return;
        latestMeasurementsByCharger.set(measurementKey(measurement), measurement);
    });
    const groupedByStation = Array.from(latestMeasurementsByCharger.values()).reduce((groups, measurement) => {
        const key = measurement.stationId;
        groups[key] = groups[key] || [];
        groups[key].push(measurement);
        return groups;
    }, {});
    Object.entries(groupedByStation).forEach(([stationId, stationMeasurements]) => {
        const stationNumber = stationNumberFromStationId(stationId);
        const station = stations.find((item) => Number(item.id) === stationNumber);
        if (!station)
            return;
        const totalPower = stationMeasurements.reduce((sum, item) => sum + Number(item.power || 0), 0);
        const activeCount = stationMeasurements.filter((item) => item.charging === true).length;
        const latestEss = stationMeasurements
            .map((item) => normalizeEssRemain(item.essRemain))
            .filter((value) => value !== null)
            .at(-1);
        station.demand = Math.round(totalPower);
        station.active = activeCount;
        station.total = Math.max(station.total, stationMeasurements.length);
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
        stationMeasurements.forEach((measurement) => {
            const chargerLabel = `DC-${String(measurement.chargerNo).padStart(2, "0")}`;
            const connectorStatus = measurement.charging ? "충전 중" : "대기";
            const powerLabel = measurement.power != null && measurement.power > 0
                ? `${measurement.power}kW`
                : "ready";
            const existingConnector = station.connectors.find((connector) => connector[0] === chargerLabel);
            if (existingConnector) {
                existingConnector[1] = connectorStatus;
                existingConnector[2] = powerLabel;
            }
            else {
                station.connectors.push([
                    chargerLabel,
                    connectorStatus,
                    powerLabel
                ]);
            }
        });
    });
}
function getVisibleStations() {
    return stations.filter((station) => {
        const matchesFilter = currentFilter === "전체" || station.status === currentFilter;
        const matchesSearch = searchQuery === "" ||
            station.name.includes(searchQuery) ||
            station.region.includes(searchQuery);
        return matchesFilter && matchesSearch;
    });
}
function getStatusClass(status) {
    if (status === "정상")
        return "ok";
    if (status === "주의")
        return "warn";
    return "alert";
}
function goToStationDetail(stationId) {
    window.location.href = `station-detail.html?id=${stationId}`;
}
function renderFilters() {
    statusFilters.innerHTML = filters
        .map((filter) => `
        <button class="filter-chip ${filter === currentFilter ? "active" : ""}" data-filter="${filter}">
          ${filter}
        </button>
      `)
        .join("");
    statusFilters.querySelectorAll(".filter-chip").forEach((button) => {
        button.addEventListener("click", () => {
            currentFilter = button.dataset.filter || "전체";
            renderAll();
        });
    });
}
function renderNodes(visibleStations) {
    stationNodes.innerHTML = visibleStations
        .map((station) => `
        <button
          class="node ${station.id === selectedStationId ? "selected" : ""}"
          data-id="${station.id}"
          style="left:${station.pos.x}%; top:${station.pos.y}%"
        >
          <div class="status-badge ${getStatusClass(station.status)}">${station.status}</div>
          <h4>${station.name}</h4>
          <p>${station.region}</p>
          <small>충전 요청 ${station.demand}kWh · 태양광 ${station.renewable}kW</small>
        </button>
      `)
        .join("");
    stationNodes.querySelectorAll(".node").forEach((node) => {
        node.addEventListener("click", () => {
            goToStationDetail(node.dataset.id);
        });
    });
}
function renderStationList(visibleStations) {
    if (!visibleStations.some((station) => station.id === selectedStationId)) {
        selectedStationId = visibleStations[0]?.id ?? stations[0].id;
    }
    stationList.innerHTML = visibleStations
        .map((station) => `
        <button class="station-card ${station.id === selectedStationId ? "selected" : ""}" data-id="${station.id}" type="button">
          <div>
            <div class="station-top">
              <h4>${station.name}</h4>
              <span class="status-badge ${getStatusClass(station.status)}">${station.status}</span>
            </div>
            <div class="station-meta">
              <span class="meta">${station.region}</span>
              <span class="meta">충전 차량 ${station.vehicles}대</span>
              <span class="meta">사용 중 충전기 ${station.active}/${station.total}</span>
            </div>
            <div class="station-tags">
              <span class="tag">충전 요청 ${station.demand}kWh</span>
              <span class="tag">배터리 ${station.ess}%</span>
              <span class="tag">태양광 ${station.renewable}kW</span>
            </div>
          </div>
          <div class="station-side">
            <span class="meta">전기요금</span>
            <strong>${station.tariff}원/kWh</strong>
            <small>${station.prediction}</small>
          </div>
        </button>
      `)
        .join("");
    stationList.querySelectorAll(".station-card").forEach((card) => {
        card.addEventListener("click", () => {
            goToStationDetail(card.dataset.id);
        });
    });
}
function renderAlgoPanel(visibleStations) {
    algoPanel.innerHTML = visibleStations
        .map((station) => `
        <article class="algo-card">
          <div class="station-top">
            <h4>${station.name}</h4>
            <span class="status-badge ${getStatusClass(station.status)}">${station.status}</span>
          </div>
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
      `)
        .join("");
}
function renderTariffs(visibleStations) {
    tariffList.innerHTML = visibleStations
        .map((station) => `
        <article class="tariff-card">
          <div class="tariff-head">
            <div>
              <h4>${station.name}</h4>
              <small>${station.region}</small>
            </div>
            <strong>${station.tariff}원/kWh</strong>
          </div>
          <p class="muted">현재 요금과 충전 수요를 반영한 권장 조치: ${station.policy}</p>
        </article>
      `)
        .join("");
}
function getStationDemand24h(station) {
    if (station.evDemand24h?.length)
        return station.evDemand24h;
    return Array.from({ length: 24 }, (_, hour) => {
        const daytimeLift = hour >= 9 && hour <= 20 ? 1.08 : 0.72;
        const peakLift = hour >= 17 && hour <= 21 ? 1.18 : 1;
        return Math.round(station.demand * daytimeLift * peakLift);
    });
}
function getStationPv24h(station) {
    if (station.pvForecast24h?.length)
        return station.pvForecast24h;
    return Array.from({ length: 24 }, (_, hour) => {
        if (hour < 7 || hour > 18)
            return 0;
        const pvIndex = Math.min(3, Math.max(0, Math.floor((hour - 7) / 3)));
        return Math.round((station.pvForecast[pvIndex] || station.renewable) * (hour >= 11 && hour <= 15 ? 1.2 : 0.7));
    });
}
function getTou24h(scope) {
    if (latestTou24h.length)
        return latestTou24h;
    const avgTariff = Math.round(scope.reduce((sum, station) => sum + station.tariff, 0) / scope.length);
    return Array.from({ length: 24 }, (_, hour) => {
        if (hour >= 17 && hour <= 21)
            return avgTariff + 24;
        if (hour >= 9 && hour <= 16)
            return avgTariff;
        return Math.max(72, avgTariff - 24);
    });
}
function renderCostComparison(visibleStations) {
    if (!costComparisonPanel)
        return;
    const scope = visibleStations.length ? visibleStations : stations;
    const tou24h = getTou24h(scope);
    const hourlyDemand = Array.from({ length: 24 }, (_, hour) => scope.reduce((sum, station) => sum + getStationDemand24h(station)[hour], 0));
    const hourlyPv = Array.from({ length: 24 }, (_, hour) => scope.reduce((sum, station) => sum + getStationPv24h(station)[hour], 0));
    const baseCost = hourlyDemand.reduce((sum, demand, hour) => sum + demand * tou24h[hour], 0);
    const policyCost = hourlyDemand.reduce((sum, demand, hour) => sum + Math.max(demand - hourlyPv[hour] * 0.9, 0) * tou24h[hour] * 0.92, 0);
    const items = [
        { label: "그냥 운영", value: baseCost, note: "추천 없이 현재 방식 유지" },
        { label: "추천 방식", value: policyCost, note: "요금과 수요를 고려해 운영" }
    ];
    costComparisonPanel.innerHTML = items
        .map((item) => {
        const saving = baseCost - item.value;
        const savingRate = baseCost > 0 ? Math.round((saving / baseCost) * 100) : 0;
        return `
        <article class="cost-card">
          <div class="cost-head">
            <div>
              <h4>${item.label}</h4>
              <small>${item.note}</small>
            </div>
            <strong>약 ${Math.round(item.value / 10000).toLocaleString()}만원</strong>
          </div>
          <p class="muted">${saving > 0 ? `그냥 운영보다 ${savingRate}% 절감` : "비교 기준"}</p>
        </article>
      `;
    })
        .join("");
}
function renderSummary(visibleStations) {
    const scope = visibleStations.length ? visibleStations : stations;
    const totalDemand = scope.reduce((sum, station) => sum + station.demand, 0);
    const avgEss = Math.round(scope.reduce((sum, station) => sum + station.ess, 0) / scope.length);
    const totalRenewable = scope.reduce((sum, station) => sum + station.pvForecast.reduce((pvSum, value) => pvSum + value, 0), 0);
    const activePorts = scope.reduce((sum, station) => sum + station.active, 0);
    const totalPorts = scope.reduce((sum, station) => sum + station.total, 0);
    const avgTariff = Math.round(scope.reduce((sum, station) => sum + station.tariff, 0) / scope.length);
    const savings = Math.round(totalDemand * 0.22);
    const busiest = scope.reduce((max, station) => station.demand > max.demand ? station : max);
    metricUptime.textContent = `${Math.round((activePorts / totalPorts) * 100)}%`;
    metricDemand.textContent = `${totalDemand}kWh`;
    metricSavings.textContent = `약 ${savings}천원`;
    summaryRequest.textContent = `${totalDemand}kWh`;
    summaryEss.textContent = `${avgEss}%`;
    if (summaryRenewable) {
        summaryRenewable.textContent = `${totalRenewable}kW`;
    }
    summaryTariff.textContent =
        avgTariff >= 135 ? "높음" : avgTariff >= 110 ? "보통" : "낮음";
    if (iotStatus) {
        iotStatus.textContent = `${scope.length} / ${scope.length} 정상`;
    }
    if (aiPolicyLabel) {
        aiPolicyLabel.textContent = `${busiest.name} 우선 확인 필요`;
    }
}
function renderAll() {
    const visibleStations = getVisibleStations();
    renderFilters();
    renderNodes(visibleStations);
    renderStationList(visibleStations);
    renderAlgoPanel(visibleStations.length ? visibleStations : stations);
    renderCostComparison(visibleStations);
    renderTariffs(visibleStations.length ? visibleStations : stations);
    renderSummary(visibleStations);
}
function tick() {
    if (liveDispatchLoaded || liveMeasurementsLoaded)
        return;
    stations.forEach((station) => {
        station.demand = Math.max(90, Math.min(360, station.demand + Math.round((Math.random() - 0.35) * 22)));
        station.ess = Math.max(28, Math.min(92, station.ess + Math.round((Math.random() - 0.52) * 8)));
        station.pvForecast = station.pvForecast.map((value) => Math.max(30, Math.min(150, value + Math.round((Math.random() - 0.45) * 10))));
        station.renewable = station.pvForecast[0];
    });
    renderAll();
}
searchInput.addEventListener("input", (event) => {
    searchQuery = event.target.value.trim();
    renderAll();
});
setupThemeControls();
renderAll();
loadLatestDispatch();
loadLatestMeasurements();
setInterval(tick, 5000);
setInterval(loadMeasurementChanges, 5000);
