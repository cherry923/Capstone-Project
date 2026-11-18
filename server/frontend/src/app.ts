// @ts-nocheck
const stations = [
    {
        id: 1,
        name: "서울 강남 허브",
        region: "서울 강남구",
        status: "정상",
        demand: 232,
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
        shareEnergyKwh: -12,
        pos: { x: 20, y: 42 },
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
        shareEnergyKwh: 30,
        pos: { x: 80, y: 48 },
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
        shareEnergyKwh: -18,
        pos: { x: 50, y: 88 },
        connectors: [
            ["AC-01", "충전 중", "120kW"],
            ["AC-03", "사용 가능", "ready"],
            ["AC-04", "사용 가능", "ready"]
        ]
    }
];
const filters = ["전체", "여유", "보통", "혼잡"];
const stationDisplayPresets = {
    "1": { name: "서울 강남 허브", region: "서울 강남구", pos: { x: 20, y: 42 } },
    "2": { name: "서울 마포 스테이션", region: "서울 마포구", pos: { x: 80, y: 48 } },
    "3": { name: "서울 송파 에너지 파크", region: "서울 송파구", pos: { x: 50, y: 88 } }
};
const stationPortCapacity = {
    "1": 5,
    "2": 3,
    "3": 3
};
const replayDemandScaleKwh = 800;
const replayPvScaleKw = 1100;
const replayDemandLevel = {
    mediumKwh: 320,
    highKwh: 550,
    mediumUseRate: 0.75,
    highUseRate: 0.9
};
const demoShareEnergyByStation = {
    "1": -12,
    "2": 30,
    "3": -18
};
const decisionModelComparison = {
    source: "EV-only volume_moderate v2 p90 peakrisk pv_ess · 3 seeds · physical oracle",
    period: "2022-01-01 ~ 2022-02-28",
    tariff: "8320 KRW/kW",
    methods: [
        {
            key: "default",
            label: "기본 운영",
            shortLabel: "Default",
            detail: "Passive-PV · ESS/SAC 없음",
            color: "#0aa99a",
            costM: 131.333,
            gridKwh: 968638,
            reductionVsGrid: 33.891,
            reductionVsPassive: 0,
            shareKwhDay: 0
        },
        {
            key: "local",
            label: "단일 SAC",
            shortLabel: "Local SAC",
            detail: "충전소별 ESS SAC",
            color: "#2878d0",
            costM: 116.52,
            gridKwh: 606640,
            reductionVsGrid: 41.348,
            reductionVsPassive: 11.279,
            shareKwhDay: 0
        },
        {
            key: "shared",
            label: "다중 SAC",
            shortLabel: "Shared PI-SAC",
            detail: "3개 충전소 P2P 공유",
            color: "#6b55d9",
            costM: 110.703,
            gridKwh: 578134,
            reductionVsGrid: 44.276,
            reductionVsPassive: 15.708,
            shareKwhDay: 977
        },
        {
            key: "soft",
            label: "Soft-MILP P2P",
            shortLabel: "Soft-MILP",
            detail: "MILP 공유 + 단일 SAC",
            color: "#5aa469",
            costM: 115.053,
            gridKwh: 599468,
            reductionVsGrid: 42.086,
            reductionVsPassive: 12.396,
            shareKwhDay: 553
        },
        {
            key: "forecast",
            label: "Forecast MILP",
            shortLabel: "Forecast MILP",
            detail: "예측 기반 rolling MILP",
            color: "#c36f18",
            costM: 111.958,
            gridKwh: 744792,
            reductionVsGrid: 43.644,
            reductionVsPassive: 14.753,
            shareKwhDay: 1378
        },
        {
            key: "oracle",
            label: "MILP + MILP",
            shortLabel: "MILP+MILP",
            detail: "60일 중앙 최적화 상한선",
            color: "#f28a21",
            costM: 95.559,
            gridKwh: 685534,
            reductionVsGrid: 51.899,
            reductionVsPassive: 27.239,
            shareKwhDay: 1720
        }
    ],
    forecastMetrics: [
        { label: "PV 시간별 오차율", value: "12.01%", note: "시간 단위 WAPE · 낮을수록 정확" },
        { label: "PV 일별 발전량 오차율", value: "4.98%", note: "일별 총 발전량 WAPE" },
        { label: "EV 시간별 오차율", value: "8.80%", note: "충전소별 시간 WAPE" },
        { label: "EV 피크 수요 오차율", value: "5.42%", note: "피크 시간대 WAPE" }
    ],
    gridSeries: {
        labels: ["00", "03", "06", "09", "12", "15", "18", "21", "23"],
        default: [1251, 1211, 1096, 978, 998, 902, 794, 503, 0, 0, 0, 0, 0, 0, 0, 0, 0, 254, 1037, 1214, 1283, 1257, 1250, 1234],
        local: [783, 759, 686, 612, 625, 565, 497, 315, 0, 0, 0, 0, 0, 0, 0, 0, 0, 159, 649, 760, 804, 787, 783, 773],
        soft: [774, 750, 678, 605, 618, 558, 491, 311, 0, 0, 0, 0, 0, 0, 0, 0, 0, 157, 642, 751, 794, 778, 773, 763],
        shared: [747, 723, 654, 584, 596, 538, 474, 300, 0, 0, 0, 0, 0, 0, 0, 0, 0, 151, 619, 724, 766, 750, 746, 736],
        forecast: [962, 931, 843, 752, 768, 694, 610, 386, 0, 0, 0, 0, 0, 0, 0, 0, 0, 195, 797, 933, 987, 966, 961, 949],
        oracle: [885, 857, 776, 692, 707, 639, 562, 356, 0, 0, 0, 0, 0, 0, 0, 0, 0, 179, 734, 859, 908, 890, 884, 873]
    },
    forecastSeries: {
        labels: ["00", "06", "12", "18", "23"],
        actual: [1251, 1211, 1096, 978, 998, 902, 794, 699, 754, 795, 782, 830, 854, 845, 831, 888, 987, 1132, 1135, 1214, 1283, 1257, 1250, 1234],
        predicted: [1285, 1194, 1087, 1030, 969, 904, 831, 793, 771, 767, 789, 781, 789, 795, 815, 858, 949, 1058, 1142, 1219, 1283, 1289, 1291, 1311]
    }
};
const decisionComparisonMethodKeys = ["default", "local", "shared", "oracle"];
const timelineBaseByStation = new Map(stations.map((station) => [
    String(station.id),
    {
        demand: Number(station.demand || 0),
        renewable: Number(station.renewable || 0),
        pvForecast: [...(station.pvForecast || [])],
        shareEnergyKwh: Number(station.shareEnergyKwh || 0)
    }
]));
let currentFilter = "전체";
let selectedStationId = 1;
let selectedMapStationId = null;
let searchQuery = "";
const stationNodes = document.getElementById("station-nodes");
const mapBoard = document.querySelector(".map-board");
const mapCanvas = document.querySelector(".map-canvas");
const mapZoomIn = document.getElementById("map-zoom-in");
const mapZoomOut = document.getElementById("map-zoom-out");
const mapZoomReset = document.getElementById("map-zoom-reset");
const timelineToggle = document.getElementById("timeline-toggle");
const timelineRange = document.getElementById("timeline-range");
const timelineTime = document.getElementById("timeline-time");
const timelineCaption = document.getElementById("timeline-caption");
const timelineDuration = document.getElementById("timeline-duration");
const energyFlows = document.getElementById("energy-flows");
const stationList = document.getElementById("station-list");
const algoPanel = document.getElementById("algo-panel");
const tariffList = document.getElementById("tariff-list");
const costComparisonPanel = document.getElementById("cost-comparison-panel");
const statusFilters = document.getElementById("status-filters");
const searchInput = document.getElementById("search-input");
const stationAddToggle = document.getElementById("station-add-toggle");
const stationAddForm = document.getElementById("station-add-form");
const stationAddCancel = document.getElementById("station-add-cancel");
const stationAddId = document.getElementById("station-add-id");
const stationAddName = document.getElementById("station-add-name");
const stationAddRegion = document.getElementById("station-add-region");
const stationAdminMessage = document.getElementById("station-admin-message");
const themeSwitcher = document.getElementById("theme-switcher");
const settingsToggle = document.getElementById("settings-toggle");
const themePopover = document.getElementById("theme-popover");
const themeStorageKey = "gridflowThemeApp";
const savedTheme = window.localStorage.getItem(themeStorageKey) || "light";
document.body.dataset.theme = savedTheme;
let mapCardsHidden = false;
const mapBaseZoom = 0.8;
let mapZoom = 1;
let timelapseFrameIndex = currentHourIndex(24);
let timelapsePlaying = false;
let timelapseTimer = null;
let mapDragState = null;
let suppressNextMapClick = false;
let activeTimelapsePeriod = null;
let activeTimelapseFrames = [];
function setMapCardsHidden(hidden) {
    mapCardsHidden = hidden;
    mapBoard?.classList.toggle("cards-hidden", mapCardsHidden);
}
function setMapZoom(nextZoom) {
    mapZoom = Math.max(0.8, Math.min(1.6, Number(nextZoom.toFixed(2))));
    mapBoard?.style.setProperty("--map-zoom", String(Number((mapZoom * mapBaseZoom).toFixed(2))));
    if (mapZoomReset) {
        mapZoomReset.textContent = `${Math.round(mapZoom * 100)}%`;
    }
    renderEnergyFlows(getVisibleStations());
}
function formatTimelineHour(hour) {
    return `${String(hour).padStart(2, "0")}:00`;
}
function getTimelapseFrameCount() {
    return activeTimelapseFrames.length || 24;
}
function frameHourFromIndex(frameIndex) {
    return Number(activeTimelapseFrames[frameIndex]?.hour ?? frameIndex % 24);
}
function formatReplayDisplayText(value) {
    return String(value || "")
        .replace(/\b(\d{4})-(\d{2})-(\d{2})\b/g, (_match, _year, month, day) => `${Number(month)}월 ${Number(day)}일`)
        .replace(/\b20\d{2}년\s*/g, "");
}
function formatTimelineDate(dateValue) {
    return formatReplayDisplayText(dateValue);
}
function formatTimelineCaptionLabel(label) {
    return formatReplayDisplayText(label || "운영 리플레이");
}
function formatTimelineFrame(frameIndex) {
    const frame = activeTimelapseFrames[frameIndex];
    const hourLabel = formatTimelineHour(frameHourFromIndex(frameIndex));
    if (frame?.date && getTimelapseFrameCount() > 24) {
        return `${formatTimelineDate(frame.date)} ${hourLabel}`;
    }
    return hourLabel;
}
function daylightCurve(hour) {
    if (hour < 6 || hour > 19)
        return 0;
    const normalized = (hour - 6) / 13;
    return Math.max(0, Math.sin(normalized * Math.PI));
}
function demandCurve(hour) {
    const morningPeak = Math.exp(-Math.pow((hour - 9) / 3.8, 2));
    const eveningPeak = Math.exp(-Math.pow((hour - 18) / 4.2, 2));
    return 0.72 + morningPeak * 0.2 + eveningPeak * 0.32;
}
function buildDemoPv24h(baseValue, stationId) {
    const stationFactor = 0.88 + (Number(stationId) % 3) * 0.08;
    const peak = Math.max(Number(baseValue || 0), 48) * 1.28 * stationFactor;
    return Array.from({ length: 24 }, (_, hour) => {
        const cloudWave = 0.9 + Math.sin((hour + Number(stationId || 1)) * 0.8) * 0.08;
        return Math.round(peak * daylightCurve(hour) * cloudWave);
    });
}
function buildDemoDemand24h(baseValue, stationId) {
    const stationFactor = 0.92 + (Number(stationId) % 3) * 0.07;
    return Array.from({ length: 24 }, (_, hour) => {
        const nightDrop = hour < 6 ? 0.62 : 1;
        return Math.round(Math.max(70, Number(baseValue || 120) * stationFactor * demandCurve(hour) * nightDrop));
    });
}
function normalizeTimelapseStationFrame(frame) {
    if (!frame)
        return null;
    const pvKw = Number(frame.pv_kw ?? frame.pvKw ?? frame.renewable ?? 0);
    const stationId = frame.station_id ?? frame.stationId;
    const rawTotal = Number(frame.total_chargers ?? frame.totalChargers ?? frame.total);
    const total = stationPortCapacity[String(stationId)] ?? rawTotal;
    const rawActive = Number(frame.active_chargers ?? frame.activeChargers ?? frame.active);
    const active = Math.min(Math.max(Number.isFinite(rawActive) ? rawActive : 0, 0), total);
    return {
        stationId,
        stationName: frame.station_name ?? frame.stationName,
        region: frame.region,
        demand: Math.round(Number(frame.demand_kwh ?? frame.demandKwh ?? frame.demand ?? 0)),
        renewable: Math.round(pvKw),
        ess: Math.round(Number(frame.ess_percent ?? frame.essPercent ?? frame.ess ?? 0)),
        tariff: Math.round(Number(frame.tariff_krw_per_kwh ?? frame.tariffKrwPerKwh ?? frame.tariff ?? 0)),
        shareEnergyKwh: Number(frame.share_energy_kwh ?? frame.shareEnergyKwh ?? 0),
        active,
        total,
        vehicles: frame.vehicle_count ?? frame.vehicleCount ?? frame.vehicles,
        status: frame.status,
        command: frame.command_text ?? frame.command,
        policy: frame.policy_text ?? frame.policy,
        prediction: formatReplayDisplayText(frame.prediction_text ?? frame.prediction),
        pvForecast: [0, 1, 2, 3].map((offset) => Math.round(pvKw * Math.max(0.55, 1 - offset * 0.08)))
    };
}
function timelineValuesForStation(station, frameIndex) {
    const persistedFrame = station.timelapseFramesByIndex?.get(frameIndex)
        || station.timelapseFramesByHour?.get(frameIndex);
    if (persistedFrame) {
        return persistedFrame;
    }
    const hour = frameHourFromIndex(frameIndex);
    const base = timelineBaseByStation.get(String(station.id)) || {};
    const pv24h = station.pvForecast24h?.length
        ? station.pvForecast24h
        : buildDemoPv24h(base.renewable ?? station.renewable, station.id);
    const demand24h = station.evDemand24h?.length
        ? station.evDemand24h
        : buildDemoDemand24h(base.demand ?? station.demand, station.id);
    const shareBase = Number(demoShareEnergyByStation[String(station.id)] ?? base.shareEnergyKwh ?? station.shareEnergyKwh ?? 0);
    const flowFactor = 0.42 + daylightCurve(hour) * 0.54 + demandCurve(hour) * 0.24;
    return {
        renewable: Math.round(Number(pv24h[hour % pv24h.length] || 0)),
        demand: Math.round(Number(demand24h[hour % demand24h.length] || station.demand || 0)),
        shareEnergyKwh: Number((shareBase * flowFactor).toFixed(1)),
        pvForecast: [0, 1, 2, 3].map((offset) => Math.round(Number(pv24h[(hour + offset) % pv24h.length] || 0)))
    };
}
function updateTimelineControls() {
    const frameCount = getTimelapseFrameCount();
    if (timelineRange) {
        timelineRange.max = String(Math.max(0, frameCount - 1));
        timelineRange.value = String(timelapseFrameIndex);
    }
    if (timelineTime) {
        timelineTime.textContent = formatTimelineFrame(timelapseFrameIndex);
    }
    if (timelineCaption) {
        timelineCaption.textContent = timelapsePlaying
            ? "리플레이 재생 중"
            : formatTimelineCaptionLabel(activeTimelapsePeriod?.label);
    }
    if (timelineDuration) {
        timelineDuration.textContent = frameCount > 24 ? `${Math.round(frameCount / 24)}d` : "24h";
    }
    if (timelineToggle) {
        timelineToggle.textContent = timelapsePlaying ? "정지" : "재생";
        timelineToggle.classList.toggle("playing", timelapsePlaying);
    }
}
function applyTimelapseFrame(frameIndex) {
    const frameCount = getTimelapseFrameCount();
    timelapseFrameIndex = ((Number(frameIndex) % frameCount) + frameCount) % frameCount;
    stations.forEach((station) => {
        const values = timelineValuesForStation(station, timelapseFrameIndex);
        station.renewable = values.renewable;
        station.demand = values.demand;
        station.shareEnergyKwh = values.shareEnergyKwh;
        station.pvForecast = values.pvForecast;
        if (Number.isFinite(values.ess)) {
            station.ess = values.ess;
        }
        if (Number.isFinite(values.tariff)) {
            station.tariff = values.tariff;
        }
        if (values.active != null) {
            station.active = Number(values.active);
        }
        if (values.total != null) {
            station.total = Number(values.total);
        }
        applyStationPortCapacity(station);
        if (values.vehicles != null) {
            station.vehicles = Number(values.vehicles);
        }
        station.status = values.status || station.status;
        station.command = values.command || station.command;
        station.policy = values.policy || station.policy;
        station.prediction = values.prediction || station.prediction;
    });
    updateTimelineControls();
}
function stopTimelapse() {
    timelapsePlaying = false;
    if (timelapseTimer) {
        window.clearInterval(timelapseTimer);
        timelapseTimer = null;
    }
    updateTimelineControls();
}
function startTimelapse() {
    if (!isReplayView) {
        return;
    }
    if (timelapseTimer) {
        window.clearInterval(timelapseTimer);
    }
    timelapsePlaying = true;
    updateTimelineControls();
    void publishTimelapseFrameToMqtt("play-start");
    timelapseTimer = window.setInterval(() => {
        applyTimelapseFrame(timelapseFrameIndex + 1);
        renderAll();
        void publishTimelapseFrameToMqtt("playback");
    }, 420);
}
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
const localHosts = ["localhost", "127.0.0.1", "::1", "[::1]"];
function isLoopbackHost(hostname) {
    return localHosts.includes(hostname);
}
function inferDefaultApiBase() {
    const staticFrontendPorts = ["3000", "4173", "4177", "4188", "5500"];
    const isLocalStaticFrontend = isLoopbackHost(window.location.hostname) &&
        staticFrontendPorts.includes(window.location.port);
    if (window.location.protocol === "file:" || isLocalStaticFrontend) {
        return "http://127.0.0.1:8080";
    }
    return "";
}
function shouldIgnoreApiBase(apiBaseCandidate) {
    if (!apiBaseCandidate || window.location.protocol === "file:" || isLoopbackHost(window.location.hostname)) {
        return false;
    }
    try {
        return isLoopbackHost(new URL(apiBaseCandidate, window.location.origin).hostname);
    }
    catch {
        return false;
    }
}
function resolveApiBase(apiBaseCandidates) {
    const resolved = apiBaseCandidates.find((candidate) => candidate && !shouldIgnoreApiBase(candidate)) || "";
    return resolved.replace(/\/$/, "");
}
const apiParams = new URLSearchParams(window.location.search);
const requestedDashboardView = (apiParams.get("view") || "").toLowerCase();
const dashboardView = requestedDashboardView === "live" || requestedDashboardView === "replay"
    ? requestedDashboardView
    : (apiParams.has("period") || apiParams.has("frame") || apiParams.has("autoplay") || apiParams.has("mqttDemo") || apiParams.has("mqttPublish") || apiParams.has("mqttMode")
        ? "replay"
        : "live");
const isReplayView = dashboardView === "replay";
document.body.dataset.dashboardView = dashboardView;
const defaultApiBase = inferDefaultApiBase();
const apiBase = resolveApiBase([
    apiParams.get("api"),
    window.localStorage.getItem("gridflowApiBase"),
    defaultApiBase
]);
const adminStationsPath = "/api/admin/stations";
const chargerMeasurementsPath = "/api/chargers/measurements";
const timelapsePeriodsPath = "/api/v1/ai/timelapse-periods";
const defaultTimelapsePeriodKey = "presentation-2022-feb-transformer-month-loop";
const demoReplayFrameIndex = 624;
const allowedTimelapsePeriodKeys = new Set([
    defaultTimelapsePeriodKey,
    "presentation-2022-jan-feb-transformer-lookahead"
]);
const timelapseMqttMode = (apiParams.get("mqttMode") || apiParams.get("mqtt") || "demo").toLowerCase() === "live"
    ? "live"
    : "demo";
const timelapseMqttPublishEnabled = ["1", "true", "yes"].includes((apiParams.get("mqttDemo") || "").toLowerCase())
    || ["1", "true", "yes"].includes((apiParams.get("mqttPublish") || "").toLowerCase())
    || (apiParams.get("mqttMode") || "").toLowerCase() === "live";
const timelapseMqttRepeatEnabled = ["1", "true", "yes"].includes((apiParams.get("mqttRepeat") || "").toLowerCase());
const publishedTimelapseMqttFrames = new Set();
let timelapseMqttPublishInFlight = false;
const metricUptime = document.getElementById("metric-uptime");
const metricDemand = document.getElementById("metric-demand");
const metricSavings = document.getElementById("metric-savings");
const summaryRequest = document.getElementById("summary-request");
const summaryEss = document.getElementById("summary-ess");
const summaryRenewable = document.getElementById("summary-renewable");
const summaryTariff = document.getElementById("summary-tariff");
const iotStatus = document.getElementById("iot-status");
const dashboardLiveLink = document.getElementById("dashboard-live-link");
const dashboardReplayLink = document.getElementById("dashboard-replay-link");
const aiPolicyLabel = document.getElementById("ai-policy-label");
const noticeBaseCost = document.getElementById("notice-base-cost");
const noticePolicyCost = document.getElementById("notice-policy-cost");
const noticeSavingRate = document.getElementById("notice-saving-rate");
let liveDispatchLoaded = false;
let liveMeasurementsLoaded = false;
let latestTou24h = [];
let managedStationIds = null;
const latestMeasurementsByCharger = new Map();
function getAdminUsername() {
    return window.sessionStorage.getItem("gridflowAdminName") || "";
}
function normalizeTimelapsePeriodKey(periodKey) {
    const normalized = (periodKey || "").trim();
    return allowedTimelapsePeriodKeys.has(normalized) ? normalized : defaultTimelapsePeriodKey;
}
function ensureReplayPeriodQuery() {
    if (!isReplayView) {
        return;
    }
    const periodKey = normalizeTimelapsePeriodKey(apiParams.get("period"));
    let changed = false;
    const url = new URL(window.location.href);
    if (apiParams.get("period") !== periodKey) {
        url.searchParams.set("period", periodKey);
        apiParams.set("period", periodKey);
        changed = true;
    }
    if (periodKey === defaultTimelapsePeriodKey && !apiParams.has("frame")) {
        url.searchParams.set("frame", String(demoReplayFrameIndex));
        apiParams.set("frame", String(demoReplayFrameIndex));
        changed = true;
    }
    if (!apiParams.has("autoplay")) {
        url.searchParams.set("autoplay", "1");
        apiParams.set("autoplay", "1");
        changed = true;
    }
    if (changed) {
        window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    }
}

function buildDashboardViewHref(view) {
    const url = new URL(window.location.href);
    url.searchParams.set("view", view);
    if (view === "live") {
        ["period", "frame", "autoplay", "mqttDemo", "mqttPublish", "mqttMode", "mqtt"].forEach((key) => {
            url.searchParams.delete(key);
        });
    }
    else {
        const periodKey = normalizeTimelapsePeriodKey(url.searchParams.get("period"));
        url.searchParams.set("period", periodKey);
        if (periodKey === defaultTimelapsePeriodKey) {
            url.searchParams.set("frame", String(demoReplayFrameIndex));
            url.searchParams.set("autoplay", "1");
        }
    }
    return `${url.pathname}${url.search}${url.hash}`;
}

function configureDashboardViewControls() {
    const links = [
        { element: dashboardLiveLink, view: "live" },
        { element: dashboardReplayLink, view: "replay" }
    ];
    links.forEach(({ element, view }) => {
        if (!element) {
            return;
        }
        element.href = buildDashboardViewHref(view);
        const isActive = dashboardView === view;
        element.classList.toggle("active", isActive);
        if (isActive) {
            element.setAttribute("aria-current", "page");
        }
        else {
            element.removeAttribute("aria-current");
        }
    });
}

function createStationModel(adminStation) {
    const index = stations.length;
    const numericId = Number(adminStation.stationId);
    return {
        id: Number.isFinite(numericId) ? numericId : adminStation.stationId,
        name: adminStation.stationName || `충전소 ${adminStation.stationId}`,
        region: adminStation.region || "지역 미지정",
        status: "정상",
        demand: 0,
        ess: 60,
        renewable: 0,
        pvForecast: [0, 0, 0, 0],
        tariff: 110,
        active: 0,
        total: 0,
        vehicles: 0,
        policy: "운영 데이터 수집 대기",
        prediction: "신규 등록 충전소",
        command: "추가 조치 없음",
        pos: { x: 18 + (index * 23) % 62, y: 18 + (index * 17) % 54 },
        connectors: [],
        shareEnergyKwh: 0,
        adminStatus: adminStation.status || "ACTIVE"
    };
}
function getStationPortCapacity(stationId, fallback = 0) {
    return stationPortCapacity[String(stationId)] ?? fallback;
}
function applyStationPortCapacity(station) {
    const capacity = getStationPortCapacity(station.id, Number(station.total || 0));
    if (!capacity) {
        return;
    }
    station.total = capacity;
    station.active = Math.min(Math.max(Number(station.active || 0), 0), capacity);
}
function applyTimelapsePeriodDetail(detail) {
    const frames = Array.isArray(detail?.frames) ? detail.frames : [];
    if (!frames.length) {
        return false;
    }
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
    activeTimelapseFrames = normalizedFrames.map((periodFrame, index) => ({
        index,
        frameIndex: periodFrame.sortIndex,
        date: periodFrame.date,
        hour: Number.isInteger(periodFrame.hour) ? periodFrame.hour : index % 24
    }));
    stations.forEach((station) => {
        station.timelapseFramesByHour = new Map();
        station.timelapseFramesByIndex = new Map();
    });
    normalizedFrames.forEach((periodFrame, frameIndex) => {
        const hour = Number.isInteger(periodFrame.hour) ? periodFrame.hour : frameIndex % 24;
        if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
            return;
        }
        periodFrame.stations.forEach((stationFrame) => {
            const normalized = normalizeTimelapseStationFrame(stationFrame);
            const stationId = String(normalized?.stationId ?? "").trim();
            if (!stationId) {
                return;
            }
            let station = stations.find((item) => String(item.id) === stationId);
            if (!station) {
                station = createStationModel({
                    stationId,
                    stationName: normalized.stationName || `충전소 ${stationId}`,
                    region: normalized.region || "지역 미지정"
                });
                stations.push(station);
            }
            station.name = normalized.stationName || station.name;
            station.region = normalized.region || station.region;
            station.timelapseFramesByHour = station.timelapseFramesByHour || new Map();
            station.timelapseFramesByIndex = station.timelapseFramesByIndex || new Map();
            station.timelapseFramesByIndex.set(frameIndex, normalized);
            if (activeTimelapseFrames.length <= 24) {
                station.timelapseFramesByHour.set(hour, normalized);
            }
        });
    });
    activeTimelapsePeriod = {
        periodKey: detail.period_key ?? detail.periodKey,
        label: detail.label,
        startDate: detail.start_date ?? detail.startDate,
        endDate: detail.end_date ?? detail.endDate,
        source: detail.source
    };
    const requestedFrame = Number(apiParams.get("frame"));
    if (Number.isInteger(requestedFrame) && requestedFrame >= 0 && requestedFrame < activeTimelapseFrames.length) {
        timelapseFrameIndex = requestedFrame;
    }
    else if (normalizeTimelapsePeriodKey(detail.period_key ?? detail.periodKey) === defaultTimelapsePeriodKey
        && demoReplayFrameIndex < activeTimelapseFrames.length) {
        timelapseFrameIndex = demoReplayFrameIndex;
    }
    else if (activeTimelapseFrames.length <= 24) {
        const currentHour = currentHourIndex(24);
        const currentHourIndexInFrames = activeTimelapseFrames.findIndex((frame) => frame.hour === currentHour);
        timelapseFrameIndex = currentHourIndexInFrames >= 0 ? currentHourIndexInFrames : Math.min(timelapseFrameIndex, activeTimelapseFrames.length - 1);
    }
    else {
        timelapseFrameIndex = Math.min(timelapseFrameIndex, activeTimelapseFrames.length - 1);
    }
    applyTimelapseFrame(timelapseFrameIndex);
    return true;
}
async function loadTimelapsePeriod() {
    if (!isReplayView) {
        return;
    }
    try {
        const periodKey = normalizeTimelapsePeriodKey(apiParams.get("period"));
        const path = `${timelapsePeriodsPath}/${encodeURIComponent(periodKey)}`;
        const response = await fetch(`${apiBase}${path}`);
        if (!response.ok) {
            return;
        }
        const body = await response.json();
        const detail = body?.data || body;
        if (applyTimelapsePeriodDetail(detail)) {
            renderAll();
            if (apiParams.get("autoplay") === "1") {
                startTimelapse();
            }
        }
    }
    catch (error) {
        console.warn("Timelapse period fetch failed; using fallback station data.", error);
    }
}
async function publishTimelapseFrameToMqtt(trigger) {
    if (!isReplayView || !timelapseMqttPublishEnabled || !activeTimelapsePeriod?.periodKey) {
        return;
    }
    const periodKey = activeTimelapsePeriod.periodKey;
    const frameIndex = timelapseFrameIndex;
    const publishKey = `${periodKey}:${frameIndex}:${timelapseMqttMode}`;
    if ((!timelapseMqttRepeatEnabled && publishedTimelapseMqttFrames.has(publishKey)) || timelapseMqttPublishInFlight) {
        return;
    }
    publishedTimelapseMqttFrames.add(publishKey);
    timelapseMqttPublishInFlight = true;
    try {
        const path = `${timelapsePeriodsPath}/${encodeURIComponent(periodKey)}/frames/${encodeURIComponent(String(frameIndex))}/mqtt-publish`;
        const params = new URLSearchParams({
            mode: timelapseMqttMode,
            trigger
        });
        const response = await fetch(`${apiBase}${path}?${params.toString()}`, {
            method: "POST"
        });
        if (!response.ok) {
            throw new Error(`MQTT publish failed: ${response.status}`);
        }
        const body = await response.json();
        const detail = body?.data || body;
        if (iotStatus) {
            const label = timelapseMqttMode === "live" ? "운영 MQTT" : "데모 MQTT";
            const hour = String(detail?.hour ?? "").padStart(2, "0");
            iotStatus.textContent = `${label} ${formatTimelineDate(detail?.frame_date)} ${hour}시 발행`;
        }
    }
    catch (error) {
        publishedTimelapseMqttFrames.delete(publishKey);
        console.warn("Timelapse MQTT publish failed.", error);
        if (iotStatus) {
            iotStatus.textContent = "MQTT 발행 실패";
        }
    }
    finally {
        timelapseMqttPublishInFlight = false;
    }
}
function syncAdminStations(adminStations) {
    managedStationIds = new Set(adminStations.map((station) => String(station.stationId)));
    for (let index = stations.length - 1; index >= 0; index -= 1) {
        if (!managedStationIds.has(String(stations[index].id))) {
            stations.splice(index, 1);
        }
    }
    adminStations.forEach((adminStation) => {
        let station = stations.find((item) => String(item.id) === String(adminStation.stationId));
        if (!station) {
            station = createStationModel(adminStation);
            stations.push(station);
        }
        const displayPreset = stationDisplayPresets[String(adminStation.stationId)];
        station.name = displayPreset?.name || adminStation.stationName || station.name;
        station.region = displayPreset?.region || adminStation.region || station.region;
        if (displayPreset?.pos) {
            station.pos = displayPreset.pos;
        }
        station.adminStatus = adminStation.status || "ACTIVE";
        if (station.name.includes("강남")) {
            station.demand = Math.max(Number(station.demand || 0), 232);
        }
        applyStationPortCapacity(station);
    });
}
async function loadAdminStations() {
    const username = getAdminUsername();
    if (!username)
        return;
    try {
        const response = await fetch(`${apiBase}${adminStationsPath}?username=${encodeURIComponent(username)}`);
        if (!response.ok)
            return;
        const body = await response.json();
        const adminStations = body?.data?.stations || [];
        if (!Array.isArray(adminStations))
            return;
        if (username === "demo" && adminStations.length === 0) {
            return;
        }
        syncAdminStations(adminStations);
        renderAll();
    }
    catch (error) {
        console.warn("Admin station fetch failed; using fallback station data.", error);
    }
}
async function addAdminStation(station) {
    const username = getAdminUsername();
    if (!username)
        throw new Error("로그인 정보가 없습니다.");
    const response = await fetch(`${apiBase}${adminStationsPath}?username=${encodeURIComponent(username)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(station)
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.code !== "SUCCESS") {
        throw new Error(body.message || "충전소 추가에 실패했습니다.");
    }
    await loadAdminStations();
}
async function removeAdminStation(stationId) {
    const username = getAdminUsername();
    if (!username)
        throw new Error("로그인 정보가 없습니다.");
    const response = await fetch(
        `${apiBase}${adminStationsPath}/${encodeURIComponent(stationId)}?username=${encodeURIComponent(username)}`,
        { method: "DELETE" }
    );
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.code !== "SUCCESS") {
        throw new Error(body.message || "충전소 제거에 실패했습니다.");
    }
    managedStationIds?.delete(String(stationId));
    const removeIndex = stations.findIndex((station) => String(station.id) === String(stationId));
    if (removeIndex >= 0) {
        stations.splice(removeIndex, 1);
    }
    await loadAdminStations();
    renderAll();
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
    const hasRealShareEnergy = commands.some((command) => Math.abs(Number(command.share_energy_kwh || 0)) > 0);
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
        const realShareEnergy = Number(hourCommand.share_energy_kwh || 0);
        station.shareEnergyKwh = hasRealShareEnergy
            ? realShareEnergy
            : Number(demoShareEnergyByStation[String(station.id)] ?? realShareEnergy);
        station.command = commandLabel(hourCommand.command);
        station.policy = `${station.command} · 전력 이동 ${Number(station.shareEnergyKwh || 0).toFixed(1)}kWh`;
        station.prediction = run.model_status
            ? "AI 추천 운영 결과 반영"
            : "추천 계산 대기";
    });
    liveDispatchLoaded = true;
}
async function loadLatestDispatch() {
    if (!isReplayView) {
        return;
    }
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
        const capacity = getStationPortCapacity(station.id, stationMeasurements.length || station.total);
        station.active = Math.min(activeCount, capacity || activeCount);
        station.total = capacity || stationMeasurements.length || station.total;
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
            const chargerLabel = `AC-${String(measurement.chargerNo).padStart(2, "0")}`;
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
    const source = getManagedStations();
    return source.filter((station) => {
        const demandLevel = getDemandLevel(station);
        const matchesFilter = currentFilter === "전체" || demandLevel.label === currentFilter;
        const matchesSearch = searchQuery === "" ||
            station.name.includes(searchQuery) ||
            station.region.includes(searchQuery) ||
            demandLevel.label.includes(searchQuery);
        return matchesFilter && matchesSearch;
    });
}
function getManagedStations() {
    return managedStationIds
        ? stations.filter((station) => managedStationIds.has(String(station.id)))
        : stations;
}
function getStatusClass(status) {
    if (status === "정상")
        return "ok";
    if (status === "주의")
        return "warn";
    return "alert";
}
function getDemandLevel(station) {
    const useRate = station.total ? station.active / station.total : 0;
    if (station.demand >= replayDemandLevel.highKwh || useRate >= replayDemandLevel.highUseRate) {
        return { className: "high", label: "혼잡" };
    }
    if (station.demand >= replayDemandLevel.mediumKwh || useRate >= replayDemandLevel.mediumUseRate) {
        return { className: "medium", label: "보통" };
    }
    return { className: "low", label: "여유" };
}
function getDemandRate(station) {
    return Math.min(100, Math.round(Number(station.demand || 0) / replayDemandScaleKwh * 100));
}
function goToStationDetail(stationId) {
    const url = new URL("station-detail.html", window.location.href);
    url.searchParams.set("id", String(stationId));
    if (isReplayView) {
        url.searchParams.set("view", "replay");
        url.searchParams.set("period", activeTimelapsePeriod?.periodKey || normalizeTimelapsePeriodKey(apiParams.get("period")));
        url.searchParams.set("frame", String(timelapseFrameIndex));
        url.searchParams.set("autoplay", apiParams.get("autoplay") || "1");
    }
    if (apiParams.has("api")) {
        url.searchParams.set("api", apiParams.get("api"));
    }
    window.location.href = url.href;
}
function getMapPoint(station) {
    return {
        x: Number(station.pos.x || 0),
        y: Number(station.pos.y || 0)
    };
}
function renderEnergyFlows(visibleStations) {
    if (!energyFlows)
        return;
    if (!isReplayView) {
        energyFlows.innerHTML = "";
        return;
    }
    const relations = buildShareRelations(visibleStations);
    if (!relations.length) {
        energyFlows.innerHTML = "";
        return;
    }
    const paths = relations
        .map((relation, index) => {
        const from = getMapPoint(relation.from);
        const to = getMapPoint(relation.to);
        const flowDuration = Math.max(0.75, Math.min(2.4, 2.4 - relation.amount / 18));
        const markerId = relation.amount >= 20 ? "energy-arrow-strong" : "energy-arrow";
        return `
          <line
            class="energy-flow-path ${relation.amount >= 20 ? "strong" : "normal"}"
            x1="${from.x}"
            y1="${from.y}"
            x2="${to.x}"
            y2="${to.y}"
            pathLength="100"
            marker-end="url(#${markerId})"
            style="--flow-duration:${flowDuration.toFixed(2)}s"
          />
        `;
    })
        .join("");
    const labels = relations
        .map((relation, index) => {
        const from = getMapPoint(relation.from);
        const to = getMapPoint(relation.to);
        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const distance = Math.max(Math.hypot(dx, dy), 1);
        const angle = Math.atan2(dy, dx) * 180 / Math.PI;
        const curve = index % 2 === 0 ? -1.6 : 1.6;
        const labelX = (from.x + to.x) / 2 + (-dy / distance) * curve;
        const labelY = (from.y + to.y) / 2 + (dx / distance) * curve;
        return `
          <span
            class="energy-flow-label ${relation.amount >= 20 ? "strong" : "normal"}"
            style="left:${labelX}%; top:${labelY}%; --flow-angle:${angle.toFixed(2)}deg"
          >
            ${relation.amount.toFixed(0)}kWh
          </span>
        `;
    })
        .join("");
    energyFlows.innerHTML = `
      <svg class="energy-flow-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <marker id="energy-arrow" viewBox="0 0 10 10" refX="8.4" refY="5" markerWidth="4.8" markerHeight="4.8" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z"></path>
          </marker>
          <marker id="energy-arrow-strong" viewBox="0 0 10 10" refX="8.4" refY="5" markerWidth="5.4" markerHeight="5.4" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z"></path>
          </marker>
        </defs>
        ${paths}
      </svg>
      ${labels}
    `;
}
function getShareDisplay(station) {
    if (!isReplayView) {
        return {
            className: "none",
            label: "공유 없음",
            value: "0kWh"
        };
    }
    const amount = Number(station.shareEnergyKwh || 0);
    if (amount > 0) {
        return {
            className: "receive",
            label: "받음",
            value: `${amount.toFixed(1)}kWh`
        };
    }
    if (amount < 0) {
        return {
            className: "send",
            label: "보냄",
            value: `${Math.abs(amount).toFixed(1)}kWh`
        };
    }
    return {
        className: "none",
        label: "공유 없음",
        value: "0kWh"
    };
}
function buildShareRelations(scope) {
    const senders = scope
        .filter((station) => Number(station.shareEnergyKwh || 0) < 0)
        .map((station) => ({
        station,
        remain: Math.abs(Number(station.shareEnergyKwh || 0))
    }));
    const receivers = scope
        .filter((station) => Number(station.shareEnergyKwh || 0) > 0)
        .map((station) => ({
        station,
        remain: Number(station.shareEnergyKwh || 0)
    }));
    const relations = [];
    senders.forEach((sender) => {
        receivers.forEach((receiver) => {
            if (sender.remain <= 0 || receiver.remain <= 0)
                return;
            const amount = Math.min(sender.remain, receiver.remain);
            relations.push({
                from: sender.station,
                to: receiver.station,
                amount
            });
            sender.remain -= amount;
            receiver.remain -= amount;
        });
    });
    return relations;
}
function getShareRows(station, scope) {
    if (!isReplayView) {
        return [{ className: "none", label: "없음", direction: "공유 연결 없음", amount: "0kWh" }];
    }
    const stationId = String(station.id);
    const relations = buildShareRelations(scope);
    const rows = relations
        .filter((relation) => String(relation.from.id) === stationId || String(relation.to.id) === stationId)
        .map((relation) => {
        const isSender = String(relation.from.id) === stationId;
        const target = isSender ? relation.to : relation.from;
        return {
            className: isSender ? "send" : "receive",
            label: isSender ? "보냄" : "받음",
            direction: target.name,
            amount: `${relation.amount.toFixed(1)}kWh`
        };
    });
    return rows.length
        ? rows
        : [{ className: "none", label: "없음", direction: "공유 연결 없음", amount: "0kWh" }];
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
    const markerHtml = visibleStations
        .map((station) => {
        const demandLevel = getDemandLevel(station);
        return `
        <button
          class="node demand-${demandLevel.className} ${String(station.id) === String(selectedMapStationId) ? "selected" : ""}"
          data-id="${station.id}"
          aria-label="${station.name} ${demandLevel.label}"
          style="--node-x:${station.pos.x}%; --node-y:${station.pos.y}%"
        ></button>
      `;
    })
        .join("");
    const popupHtml = visibleStations
        .map((station, index) => {
        const demandLevel = getDemandLevel(station);
        const demandRate = getDemandRate(station);
        const solarRate = Math.min(100, Math.round(Number(station.renewable || 0) / replayPvScaleKw * 100));
        const shareDisplay = getShareDisplay(station);
        const shareRows = getShareRows(station, getManagedStations())
            .map((row) => `
              <div class="popup-share-row ${row.className}">
                <span>${row.label}</span>
                <strong>${row.direction}</strong>
                <b>${row.amount}</b>
              </div>
            `)
            .join("");
        return `
        <article
          class="map-popup demand-${demandLevel.className} ${String(station.id) === String(selectedMapStationId) ? "selected" : ""}"
          data-popup-order="${index}"
          data-id="${station.id}"
          style="--popup-x:${station.pos.x}%; --popup-y:${station.pos.y}%"
        >
          <div class="map-popup-head">
            <div>
              <strong>${station.name}</strong>
              <span>${station.region}</span>
            </div>
            <span class="demand-badge ${demandLevel.className}">수요 ${demandLevel.label}</span>
          </div>
          <div class="popup-demand">
            <span>충전수요</span>
            <b>${station.demand}kWh</b>
            <i><em style="width:${demandRate}%"></em></i>
          </div>
          <div class="popup-solar">
            <span>태양광 발전량</span>
            <b>${station.renewable}kW</b>
            <i><em style="width:${solarRate}%"></em></i>
          </div>
          <div class="popup-share ${shareDisplay.className}">
            <span>충전공유량</span>
            <strong>${shareDisplay.label}</strong>
            <b>${shareDisplay.value}</b>
          </div>
          <div class="popup-share-detail">
            ${shareRows}
          </div>
          <button class="map-detail-button" data-detail-id="${station.id}" type="button">상세 보기</button>
        </article>
      `;
    })
        .join("");
    stationNodes.innerHTML = markerHtml + popupHtml;
    stationNodes.querySelectorAll(".node").forEach((node) => {
        node.addEventListener("click", () => {
            const clickedStationId = node.dataset.id;
            selectedMapStationId = clickedStationId;
            selectedStationId = clickedStationId;
            setMapCardsHidden(false);
            renderAll();
        });
    });
    stationNodes.querySelectorAll(".map-popup").forEach((popup) => {
        popup.addEventListener("click", () => {
            const clickedStationId = popup.dataset.id;
            selectedMapStationId = clickedStationId;
            selectedStationId = clickedStationId;
            setMapCardsHidden(false);
            renderAll();
        });
    });
    stationNodes.querySelectorAll(".map-detail-button").forEach((button) => {
        button.addEventListener("click", () => {
            goToStationDetail(button.dataset.detailId);
        });
    });
}
function renderStationList(visibleStations) {
    if (!visibleStations.length) {
        stationList.innerHTML = `
          <div class="empty-state">
            <strong>등록된 충전소가 없습니다.</strong>
            <p>충전소 추가 버튼으로 관리 대상을 등록하세요.</p>
          </div>
        `;
        return;
    }
    if (!visibleStations.some((station) => String(station.id) === String(selectedStationId))) {
        selectedStationId = visibleStations[0]?.id ?? stations[0].id;
    }
    stationList.innerHTML = visibleStations
        .map((station) => {
        const demandLevel = getDemandLevel(station);
        return `
        <article class="station-card ${String(station.id) === String(selectedStationId) ? "selected" : ""}" data-id="${station.id}">
          <button class="station-card-main" data-id="${station.id}" type="button">
            <div class="station-top">
              <h4>${station.name}</h4>
              <span class="demand-badge ${demandLevel.className}">수요 ${demandLevel.label}</span>
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
          </button>
          <div class="station-side">
            <span class="meta">전기요금</span>
            <strong>${station.tariff}원/kWh</strong>
            <small>${station.prediction}</small>
            <button class="station-remove-button" data-id="${station.id}" type="button">제거</button>
          </div>
        </article>
      `;
    })
        .join("");
    stationList.querySelectorAll(".station-card-main").forEach((card) => {
        card.addEventListener("click", () => {
            goToStationDetail(card.dataset.id);
        });
    });
    stationList.querySelectorAll(".station-remove-button").forEach((button) => {
        button.addEventListener("click", async (event) => {
            event.preventDefault();
            event.stopPropagation();
            button.disabled = true;
            stationAdminMessage.textContent = "충전소 제거 중...";
            try {
                await removeAdminStation(button.dataset.id);
                stationAdminMessage.textContent = "충전소가 제거되었습니다.";
            }
            catch (error) {
                stationAdminMessage.textContent = error.message;
                button.disabled = false;
            }
        });
    });
}
function renderAlgoPanel(visibleStations) {
    algoPanel.innerHTML = visibleStations
        .map((station) => {
        const demandLevel = getDemandLevel(station);
        return `
        <article class="algo-card">
          <div class="station-top">
            <h4>${station.name}</h4>
            <span class="demand-badge ${demandLevel.className}">수요 ${demandLevel.label}</span>
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
      `;
    })
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
function formatCostManwon(value) {
    return `약 ${Math.round(value / 10000).toLocaleString()}만원`;
}
function formatCostMillionAsManwon(value) {
    return `약 ${Math.round(value * 100).toLocaleString()}만원`;
}
function calculateOperationCosts(scope) {
    const tou24h = getTou24h(scope);
    const hourlyDemand = Array.from({ length: 24 }, (_, hour) => scope.reduce((sum, station) => sum + getStationDemand24h(station)[hour], 0));
    const hourlyPv = Array.from({ length: 24 }, (_, hour) => scope.reduce((sum, station) => sum + getStationPv24h(station)[hour], 0));
    const baseCost = hourlyDemand.reduce((sum, demand, hour) => sum + demand * tou24h[hour], 0);
    const policyCost = hourlyDemand.reduce((sum, demand, hour) => sum + Math.max(demand - hourlyPv[hour] * 0.9, 0) * tou24h[hour] * 0.92, 0);
    const saving = baseCost - policyCost;
    const savingRate = baseCost > 0 ? Math.round((saving / baseCost) * 100) : 0;
    return { baseCost, policyCost, saving, savingRate };
}
function renderNoticeComparison(scope) {
    if (!noticeBaseCost || !noticePolicyCost || !noticeSavingRate)
        return;
    if (!scope.length) {
        noticeBaseCost.textContent = "약 0만원";
        noticePolicyCost.textContent = "약 0만원";
        noticeSavingRate.textContent = "0% 절감";
        return;
    }
    const defaultMethod = decisionModelComparison.methods.find((method) => method.key === "default");
    const sharedMethod = decisionModelComparison.methods.find((method) => method.key === "shared");
    if (!defaultMethod || !sharedMethod) {
        const { baseCost, policyCost, saving, savingRate } = calculateOperationCosts(scope);
        noticeBaseCost.textContent = formatCostManwon(baseCost);
        noticePolicyCost.textContent = formatCostManwon(policyCost);
        noticeSavingRate.textContent = saving > 0 ? `${savingRate}% 절감` : "차이 없음";
        return;
    }
    noticeBaseCost.textContent = formatCostMillionAsManwon(defaultMethod.costM);
    noticePolicyCost.textContent = formatCostMillionAsManwon(sharedMethod.costM);
    noticeSavingRate.textContent = `${formatReduction(sharedMethod.reductionVsPassive)} 절감`;
}
function formatMillionKrw(value) {
    return `${Number(value).toLocaleString("ko-KR", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3
    })}M`;
}
function formatReduction(value) {
    return `${Math.abs(value).toFixed(1)}%`;
}
function formatCompactKwh(value) {
    return `${Math.round(value).toLocaleString("ko-KR")}kWh`;
}
function getSeriesBounds(seriesList) {
    const values = seriesList.flat();
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = Math.max((max - min) * 0.12, 1);
    return { min: min - padding, max: max + padding };
}
function toPolylinePoints(values, bounds, width = 620, height = 214) {
    const pad = { top: 18, right: 18, bottom: 34, left: 42 };
    const usableWidth = width - pad.left - pad.right;
    const usableHeight = height - pad.top - pad.bottom;
    const span = Math.max(bounds.max - bounds.min, 1);
    return values
        .map((value, index) => {
        const x = pad.left + (usableWidth * index) / Math.max(values.length - 1, 1);
        const y = pad.top + usableHeight - ((value - bounds.min) / span) * usableHeight;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
        .join(" ");
}
function renderLineChartSvg(series, className = "") {
    const width = 620;
    const height = 214;
    const bounds = getSeriesBounds(series.map((item) => item.values));
    const gridRows = [0, 1, 2, 3].map((row) => {
        const y = 18 + ((height - 52) * row) / 3;
        return `<line x1="42" x2="${width - 18}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}"></line>`;
    }).join("");
    const lines = series
        .map((item) => `
        <polyline
          points="${toPolylinePoints(item.values, bounds, width, height)}"
          fill="none"
          stroke="${item.color}"
          stroke-width="${item.width || 4}"
          stroke-linecap="round"
          stroke-linejoin="round"
          opacity="${item.opacity || 1}"
        ></polyline>
      `)
        .join("");
    return `
      <svg class="comparison-svg ${className}" viewBox="0 0 ${width} ${height}" role="img" aria-label="24시간 그래프">
        <g class="comparison-grid">${gridRows}</g>
        ${lines}
      </svg>
    `;
}
function renderDecisionLegend(items) {
    return items
        .map((item) => `
        <span class="decision-legend-item">
          <i style="background:${item.color}"></i>${item.label}
        </span>
      `)
        .join("");
}
function renderCostComparison(visibleStations) {
    if (!costComparisonPanel)
        return;
    const methods = decisionComparisonMethodKeys
        .map((key) => decisionModelComparison.methods.find((method) => method.key === key))
        .filter(Boolean);
    const bestMethod = methods.reduce((best, method) => method.costM < best.costM ? method : best, methods[0]);
    const defaultMethod = methods.find((method) => method.key === "default") || methods[0];
    const sharedMethod = methods.find((method) => method.key === "shared") || methods[0];
    const localMethod = methods.find((method) => method.key === "local") || methods[0];
    const maxReduction = Math.max(...methods.map((method) => method.reductionVsPassive), 1);
    const chartSeries = methods.map((method) => ({
        label: method.shortLabel,
        color: method.color,
        values: decisionModelComparison.gridSeries[method.key],
        width: method.key === "shared" ? 5 : 4,
        opacity: method.key === "default" ? 0.82 : 1
    }));
    const forecastChart = renderLineChartSvg([
        {
            label: "Actual",
            color: "#0aa99a",
            values: decisionModelComparison.forecastSeries.actual,
            width: 5
        },
        {
            label: "Forecast",
            color: "#2878d0",
            values: decisionModelComparison.forecastSeries.predicted,
            width: 4
        }
    ], "forecast-svg");
    costComparisonPanel.innerHTML = `
      <div class="decision-kpis">
        <article class="decision-kpi-card">
          <span>최저 비용 기준</span>
          <strong>${bestMethod.label}</strong>
          <p>Passive-PV 대비 ${formatReduction(bestMethod.reductionVsPassive)} 절감</p>
        </article>
        <article class="decision-kpi-card">
          <span>기본 운영 비용</span>
          <strong>${formatMillionKrw(defaultMethod.costM)}</strong>
          <p>Passive-PV · grid ${formatCompactKwh(defaultMethod.gridKwh)}</p>
        </article>
        <article class="decision-kpi-card">
          <span>공유 전력량</span>
          <strong>${formatCompactKwh(sharedMethod.shareKwhDay)}/day</strong>
          <p>${sharedMethod.label} 기준</p>
        </article>
        <article class="decision-kpi-card accent">
          <span>예측모델 상태</span>
          <strong>${decisionModelComparison.forecastMetrics[0].value}</strong>
          <p>${decisionModelComparison.forecastMetrics[0].note}</p>
        </article>
      </div>

      <div class="decision-layout">
        <article class="decision-rate-card">
          <div class="decision-card-head">
            <div>
              <span>총 전력비용</span>
              <h4>Passive-PV 대비 절감률</h4>
            </div>
            <small>${formatReplayDisplayText(decisionModelComparison.period)}</small>
          </div>
          <div class="decision-rate-list">
            ${methods
        .map((method) => {
        const width = Math.max(method.key === "default" ? 3 : 6, (method.reductionVsPassive / maxReduction) * 100);
        return `
                <div class="decision-rate-row" style="--method-color:${method.color};--method-width:${width.toFixed(1)}%">
                  <div class="decision-method-copy">
                    <strong>${method.label}</strong>
                    <span>${method.detail}</span>
                    <em>${formatMillionKrw(method.costM)} · Passive-PV 대비 절감 ${formatReduction(method.reductionVsPassive)}</em>
                  </div>
                  <div class="decision-bar-track"><span></span></div>
                  <b>${formatReduction(method.reductionVsPassive)} 절감</b>
                </div>
              `;
    })
        .join("")}
          </div>
        </article>

        <article class="decision-chart-card">
          <div class="decision-card-head">
            <div>
              <span>시간대별 Grid 사용량</span>
              <h4>대표 24시간 부하 흐름</h4>
            </div>
            <small>kWh</small>
          </div>
          ${renderLineChartSvg(chartSeries)}
          <div class="decision-chart-labels">
            ${decisionModelComparison.gridSeries.labels.map((label) => `<span>${label}</span>`).join("")}
          </div>
          <div class="decision-legend">
            ${renderDecisionLegend(chartSeries)}
          </div>
        </article>
      </div>

      <div class="forecast-model-strip">
        <article class="forecast-score-card">
          <div class="decision-card-head">
            <div>
              <span>Forecast Model</span>
              <h4>예측모델 성능</h4>
            </div>
            <small>${decisionModelComparison.source}</small>
          </div>
          <div class="model-score-grid">
            ${decisionModelComparison.forecastMetrics
        .map((metric) => `
                <div>
                  <span>${metric.label}</span>
                  <strong>${metric.value}</strong>
                  <small>${metric.note}</small>
                </div>
              `)
        .join("")}
          </div>
        </article>

        <article class="forecast-chart-card">
          <div class="decision-card-head">
            <div>
              <span>EV Demand Forecast</span>
              <h4>실측과 예측 흐름</h4>
            </div>
            <small>24h sample</small>
          </div>
          ${forecastChart}
          <div class="decision-chart-labels compact">
            ${decisionModelComparison.forecastSeries.labels.map((label) => `<span>${label}</span>`).join("")}
          </div>
          <div class="decision-legend">
            ${renderDecisionLegend([
        { label: "실측 EV 수요", color: "#0aa99a" },
        { label: "Transformer 예측", color: "#2878d0" }
    ])}
          </div>
        </article>
      </div>

      <div class="experiment-note-grid">
        <article>
          <span>비교 기준</span>
          <strong>Passive-PV 대비 절감률 표시</strong>
          <p>기본 운영은 0.0% 절감 기준이고, 막대 길이는 절감률 크기를 나타낸다.</p>
        </article>
        <article>
          <span>ESS 비대칭</span>
          <strong>5/2/5MWh · ess_ratio 0.10</strong>
          <p>station1을 작은 ESS 수신 측으로 둔 asym525 계열 시나리오다.</p>
        </article>
        <article>
          <span>공유 효과</span>
          <strong>${formatReduction(Math.abs(sharedMethod.reductionVsPassive - localMethod.reductionVsPassive))}p 추가 절감</strong>
          <p>단일 SAC 대비 공유 PI-SAC의 물리 제약 반영 추가 개선폭이다.</p>
        </article>
      </div>
    `;
}
function renderSummary(visibleStations) {
    const scope = visibleStations.length ? visibleStations : getManagedStations();
    if (!scope.length) {
        metricUptime.textContent = "0%";
        metricDemand.textContent = "0kWh";
        metricSavings.textContent = "약 0천원";
        summaryRequest.textContent = "0kWh";
        summaryEss.textContent = "0%";
        summaryTariff.textContent = "낮음";
        if (iotStatus) {
            iotStatus.textContent = "0개 충전소";
        }
        return;
    }
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
        iotStatus.textContent = isReplayView
            ? `리플레이 ${scope.length}개 충전소`
            : `실시간 ${scope.length}개 충전소`;
    }
    if (aiPolicyLabel) {
        aiPolicyLabel.textContent = `${busiest.name} 우선 확인 필요`;
    }
}
function renderAll() {
    if (isReplayView) {
        applyTimelapseFrame(timelapseFrameIndex);
    }
    else {
        updateTimelineControls();
    }
    const visibleStations = getVisibleStations();
    const operationScope = visibleStations.length ? visibleStations : getManagedStations();
    renderFilters();
    renderEnergyFlows(visibleStations);
    renderNodes(visibleStations);
    renderStationList(visibleStations);
    renderAlgoPanel(operationScope);
    renderCostComparison(visibleStations);
    renderTariffs(operationScope);
    renderSummary(visibleStations);
    renderNoticeComparison(operationScope);
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
stationAddToggle?.addEventListener("click", () => {
    stationAddForm.hidden = false;
    stationAdminMessage.textContent = "";
    stationAddId.focus();
});
stationAddCancel?.addEventListener("click", () => {
    stationAddForm.hidden = true;
    stationAdminMessage.textContent = "";
    stationAddForm.reset();
});
stationAddForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const stationId = stationAddId.value.trim();
    const stationName = stationAddName.value.trim();
    const region = stationAddRegion.value.trim();
    if (!stationId || !stationName || !region) {
        stationAdminMessage.textContent = "충전소 ID, 충전소명, 지역을 모두 입력하세요.";
        return;
    }
    stationAdminMessage.textContent = "충전소 추가 중...";
    try {
        await addAdminStation({ stationId, stationName, region });
        stationAdminMessage.textContent = "충전소가 추가되었습니다.";
        stationAddForm.reset();
        stationAddForm.hidden = true;
    }
    catch (error) {
        stationAdminMessage.textContent = error.message;
    }
});
mapBoard?.addEventListener("click", (event) => {
    if (suppressNextMapClick) {
        suppressNextMapClick = false;
        return;
    }
    const target = event.target;
    if (target.closest(".map-popup, .node, .map-detail-button, .map-zoom-controls, .map-time-controls")) {
        return;
    }
    setMapCardsHidden(!mapCardsHidden);
});
mapBoard?.addEventListener("pointerdown", (event) => {
    const target = event.target;
    if (target.closest(".map-popup, .node, .map-detail-button, .map-zoom-controls, .map-time-controls")) {
        return;
    }
    mapDragState = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        scrollLeft: mapBoard.scrollLeft,
        scrollTop: mapBoard.scrollTop,
        moved: false
    };
    mapBoard.classList.add("is-dragging");
    mapBoard.setPointerCapture?.(event.pointerId);
});
mapBoard?.addEventListener("pointermove", (event) => {
    if (!mapDragState || mapDragState.pointerId !== event.pointerId)
        return;
    const dx = event.clientX - mapDragState.startX;
    const dy = event.clientY - mapDragState.startY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
        mapDragState.moved = true;
    }
    mapBoard.scrollLeft = mapDragState.scrollLeft - dx;
    mapBoard.scrollTop = mapDragState.scrollTop - dy;
});
function finishMapDrag(event) {
    if (!mapDragState || mapDragState.pointerId !== event.pointerId)
        return;
    suppressNextMapClick = mapDragState.moved;
    mapDragState = null;
    mapBoard?.classList.remove("is-dragging");
}
mapBoard?.addEventListener("pointerup", finishMapDrag);
mapBoard?.addEventListener("pointercancel", finishMapDrag);
mapZoomIn?.addEventListener("click", (event) => {
    event.stopPropagation();
    setMapZoom(mapZoom + 0.1);
});
mapZoomOut?.addEventListener("click", (event) => {
    event.stopPropagation();
    setMapZoom(mapZoom - 0.1);
});
mapZoomReset?.addEventListener("click", (event) => {
    event.stopPropagation();
    setMapZoom(1);
});
timelineToggle?.addEventListener("click", (event) => {
    event.stopPropagation();
    if (timelapsePlaying) {
        stopTimelapse();
        return;
    }
    startTimelapse();
});
let timelineScrubbing = false;
function clampTimelineFrameIndex(value) {
    return Math.min(Math.max(0, Math.round(Number(value) || 0)), Math.max(0, getTimelapseFrameCount() - 1));
}
function commitTimelineFrame(frameIndex) {
    if (!isReplayView) {
        return;
    }
    const nextFrameIndex = clampTimelineFrameIndex(frameIndex);
    if (timelineRange) {
        timelineRange.value = String(nextFrameIndex);
    }
    stopTimelapse();
    applyTimelapseFrame(nextFrameIndex);
    renderAll();
    void publishTimelapseFrameToMqtt("scrub");
}
function timelineFrameFromPointer(event) {
    if (!timelineRange) {
        return timelapseFrameIndex;
    }
    const rect = timelineRange.getBoundingClientRect();
    const ratio = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0;
    return clampTimelineFrameIndex(ratio * Math.max(0, getTimelapseFrameCount() - 1));
}
function setTimelineFrameFromControl(event) {
    event.stopPropagation();
    commitTimelineFrame(event.target.value);
}
timelineRange?.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    event.stopPropagation();
    timelineScrubbing = true;
    timelineRange.setPointerCapture?.(event.pointerId);
    commitTimelineFrame(timelineFrameFromPointer(event));
});
timelineRange?.addEventListener("pointermove", (event) => {
    event.stopPropagation();
    if (!timelineScrubbing) {
        return;
    }
    event.preventDefault();
    commitTimelineFrame(timelineFrameFromPointer(event));
});
timelineRange?.addEventListener("pointerup", (event) => {
    event.stopPropagation();
    timelineScrubbing = false;
    timelineRange.releasePointerCapture?.(event.pointerId);
});
timelineRange?.addEventListener("pointercancel", (event) => {
    event.stopPropagation();
    timelineScrubbing = false;
    timelineRange.releasePointerCapture?.(event.pointerId);
});
timelineRange?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
});
timelineRange?.addEventListener("keydown", (event) => {
    event.stopPropagation();
    const current = Number(timelineRange.value || timelapseFrameIndex);
    const frameCount = getTimelapseFrameCount();
    const keySteps = {
        ArrowLeft: -1,
        ArrowDown: -1,
        ArrowRight: 1,
        ArrowUp: 1,
        PageDown: -24,
        PageUp: 24
    };
    if (event.key === "Home") {
        event.preventDefault();
        commitTimelineFrame(0);
        return;
    }
    if (event.key === "End") {
        event.preventDefault();
        commitTimelineFrame(frameCount - 1);
        return;
    }
    const step = keySteps[event.key];
    if (step) {
        event.preventDefault();
        commitTimelineFrame(current + step);
    }
});
timelineRange?.addEventListener("input", setTimelineFrameFromControl);
timelineRange?.addEventListener("change", setTimelineFrameFromControl);
setupThemeControls();
ensureReplayPeriodQuery();
configureDashboardViewControls();
setMapZoom(1);
if (isReplayView) {
    applyTimelapseFrame(timelapseFrameIndex);
}
else {
    updateTimelineControls();
}
renderAll();
loadTimelapsePeriod();
loadAdminStations();
loadLatestDispatch();
loadLatestMeasurements();
setInterval(tick, 5000);
setInterval(loadMeasurementChanges, 5000);
