// @ts-nocheck
const operationComparisonDataUrl = "assets/operation-comparison/evonly_vmoderate_v2p90_pvess_multiseed.json";
const operationDateSelect = document.getElementById("operation-date-select");
const operationResultBars = document.getElementById("operation-result-bars");
const operationPvChart = document.getElementById("operation-pv-chart");
const operationGridChart = document.getElementById("operation-grid-chart");
const operationStationDemandChart = document.getElementById("operation-station-demand-chart");
const operationForecastMetrics = document.getElementById("operation-forecast-metrics");
const operationStationBreakdown = document.getElementById("operation-station-breakdown");
const operationDateChip = document.getElementById("operation-date-chip");
const operationForecastDetailLink = document.getElementById("operation-forecast-detail-link");
let operationComparisonData = window.operationComparisonData || null;

function operationFormatKwh(value) {
    return `${Math.round(Number(value)).toLocaleString("ko-KR")}kWh`;
}

function operationFormatM(value) {
    return `${Number(value).toLocaleString("ko-KR", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3
    })}M`;
}

function operationFormatPct(value) {
    return `${Number(value).toFixed(1)}%`;
}

function operationPrimaryReduction(method) {
    return Number(method.reductionVsDefaultPct ?? 0);
}

function operationRemainingCostPct(method) {
    return Math.max(0, Math.min(100, 100 - operationPrimaryReduction(method)));
}

function operationDisplayDetail(method) {
    if (method.key === "milpMilp")
        return "미래정보 기반 전체 충전소 최적 운영";
    return method.detail;
}

const operationComparisonMethodKeys = ["default", "localSac", "sharedSac", "milpMilp"];
const operationStationDisplayNames = new Map([
    ["1", "강남 허브"],
    ["2", "마포 스테이션"],
    ["3", "송파 에너지 파크"],
    ["ST001", "강남 허브"],
    ["ST002", "마포 스테이션"],
    ["ST003", "송파 에너지 파크"]
]);

function operationStationDisplayLabel(station) {
    const rawStation = String(station.station ?? station.stationId ?? station.station_id ?? station.id ?? "").trim();
    const normalizedStation = rawStation.replace(/^ST0*/i, "");
    return operationStationDisplayNames.get(rawStation.toUpperCase())
        || operationStationDisplayNames.get(normalizedStation)
        || station.label
        || rawStation;
}

function operationLineBounds(series) {
    const values = series.flatMap((item) => item.values).filter((value) => Number.isFinite(value));
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 1);
    const padding = Math.max((max - min) * 0.12, 1);
    return { min: Math.max(0, min - padding), max: max + padding };
}

function operationPolyline(values, bounds, width = 680, height = 280) {
    const pad = { top: 22, right: 20, bottom: 42, left: 48 };
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

function operationChart(series, labels, ariaLabel) {
    const width = 680;
    const height = 280;
    const bounds = operationLineBounds(series);
    const grid = [0, 1, 2, 3].map((row) => {
        const y = 22 + ((height - 64) * row) / 3;
        return `<line x1="48" x2="${width - 20}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}"></line>`;
    }).join("");
    const lines = series.map((item) => `
      <polyline
        points="${operationPolyline(item.values, bounds, width, height)}"
        fill="none"
        stroke="${item.color}"
        stroke-width="${item.width || 4}"
        ${item.dashArray ? `stroke-dasharray="${item.dashArray}"` : ""}
        stroke-linecap="round"
        stroke-linejoin="round"
        opacity="${item.opacity ?? 1}"
      ></polyline>
    `).join("");
    const tickCount = labels.length;
    const ticks = labels.map((label, index) => {
        const x = 48 + ((width - 68) * index) / Math.max(tickCount - 1, 1);
        return `<span style="left:${(x / width * 100).toFixed(2)}%">${label}</span>`;
    }).join("");
    const legend = series.map((item) => `
      <span class="operation-legend-item ${item.dashArray ? "dashed" : ""}">
        <svg class="operation-legend-swatch" viewBox="0 0 34 12" aria-hidden="true">
          <line
            x1="2"
            x2="32"
            y1="6"
            y2="6"
            stroke="${item.color}"
            stroke-width="4"
            stroke-linecap="round"
            ${item.dashArray ? `stroke-dasharray="${item.dashArray}"` : ""}
          ></line>
        </svg>
        ${item.label}
      </span>
    `).join("");
    return `
      <div class="operation-chart-scroll">
        <svg class="operation-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${ariaLabel}">
          <g class="operation-svg-grid">${grid}</g>
          ${lines}
        </svg>
        <div class="operation-axis-labels">${ticks}</div>
      </div>
      <div class="operation-legend">${legend}</div>
    `;
}

function getOperationDateFromUrl(data) {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("date");
    if (requested && data.days.some((day) => day.date === requested))
        return requested;
    return data.meta.recommendedDate || data.days[0]?.date;
}

function getOperationDay(data, date) {
    return data.days.find((day) => day.date === date) || data.days[0];
}

function renderOperationDateOptions(data, selectedDate) {
    if (!operationDateSelect)
        return;
    operationDateSelect.innerHTML = data.days
        .map((day) => `<option value="${day.date}" ${day.date === selectedDate ? "selected" : ""}>${day.date}</option>`)
        .join("");
}

function renderOperationSummary(data) {
    if (!operationResultBars)
        return;
    const methodMap = new Map(data.methods.map((method) => [method.key, method]));
    const visibleMethods = operationComparisonMethodKeys.map((key) => methodMap.get(key)).filter(Boolean);
    operationResultBars.innerHTML = visibleMethods.map((method) => {
        const passiveReduction = operationPrimaryReduction(method);
        const width = operationRemainingCostPct(method);
        const recommendedClass = method.key === "sharedSac" ? "recommended" : "";
        return `
          <article class="operation-result-bar-row ${recommendedClass}" style="--bar:${width.toFixed(2)}%; --bar-color:${method.color}">
            <div class="operation-result-bar-label">
              <strong>${method.label}</strong>
              <span>${operationDisplayDetail(method)} · ${operationFormatM(method.totalCostM)} KRW</span>
            </div>
            <div class="operation-result-bar-track"><i></i></div>
            <em>${operationFormatPct(passiveReduction)} 절감</em>
          </article>
        `;
    }).join("");
}

function renderPvChart(day) {
    if (!operationPvChart)
        return;
    const labels = ["00", "03", "06", "09", "12", "15", "18", "21", "23"];
    operationPvChart.innerHTML = operationChart([
        { label: "PV 실제", color: "#0aa99a", values: day.hours.map((hour) => hour.pvActual), width: 5 },
        { label: "PV 예측", color: "#7bbf5b", values: day.hours.map((hour) => hour.pvForecast), width: 4, opacity: 0.8, dashArray: "7 7" }
    ], labels, `${day.date} PV 실제 예측 그래프`);
}

function renderGridChart(data, day) {
    if (!operationGridChart)
        return;
    const labels = ["00", "03", "06", "09", "12", "15", "18", "21", "23"];
    const methodMap = new Map(data.methods.map((method) => [method.key, method]));
    const chartMethods = operationComparisonMethodKeys.map((key) => methodMap.get(key)).filter(Boolean);
    operationGridChart.innerHTML = operationChart(chartMethods.map((method) => ({
        label: method.label,
        color: method.color,
        values: day.hours.map((hour) => hour.grid[method.key]),
        width: method.key === "sharedSac" ? 5 : 4
    })), labels, `${day.date} 운영 기준별 Grid 사용량`);
}

function renderStationDemandChart(day) {
    if (!operationStationDemandChart)
        return;
    const labels = ["00", "03", "06", "09", "12", "15", "18", "21", "23"];
    const series = day.stationDemandHours || [];
    const chartSeries = series.flatMap((station) => {
        const label = operationStationDisplayLabel(station);
        return [
            {
                label: `${label} 실제`,
                color: station.color,
                values: station.values,
                width: station.station === "2" ? 5 : 4
            },
            {
                label: `${label} 예측`,
                color: station.color,
                values: station.forecastValues || station.values,
                width: station.station === "2" ? 4 : 3,
                opacity: 0.72,
                dashArray: "7 7"
            }
        ];
    });
    operationStationDemandChart.innerHTML = operationChart(chartSeries, labels, `${day.date} 충전소별 EV 실제 예측 수요 그래프`);
}

function renderOperationModelPanel(data, day) {
    if (operationForecastMetrics) {
        operationForecastMetrics.innerHTML = data.forecastMetrics.map((metric) => `
          <article>
            <span>${metric.label}</span>
            <strong>${metric.value}${metric.unit}</strong>
            <p>${metric.note}</p>
          </article>
        `).join("");
    }
    if (operationStationBreakdown) {
        operationStationBreakdown.innerHTML = day.stations.map((station) => `
          <article>
            <span>${operationStationDisplayLabel(station)}</span>
            <strong>${operationFormatKwh(station.evActual)}</strong>
            <p>PV ${operationFormatKwh(station.pvActual)} · 기본 Grid ${operationFormatKwh(station.defaultGrid)}</p>
          </article>
        `).join("");
    }
}

function renderOperationDetail(date) {
    const data = operationComparisonData;
    const day = getOperationDay(data, date);
    if (!day)
        return;
    if (operationDateChip)
        operationDateChip.textContent = day.date;
    if (operationForecastDetailLink)
        operationForecastDetailLink.href = `forecast-detail.html?date=${encodeURIComponent(day.date)}`;
    renderOperationSummary(data);
    renderPvChart(day);
    renderGridChart(data, day);
    renderStationDemandChart(day);
    renderOperationModelPanel(data, day);
}

async function initOperationDetail() {
    if (!operationDateSelect)
        return;
    if (!operationComparisonData) {
        try {
            const response = await fetch(operationComparisonDataUrl);
            operationComparisonData = await response.json();
        }
        catch (error) {
            console.warn("Operation comparison data fetch failed", error);
            return;
        }
    }
    const selectedDate = getOperationDateFromUrl(operationComparisonData);
    renderOperationDateOptions(operationComparisonData, selectedDate);
    renderOperationDetail(selectedDate);
    operationDateSelect.addEventListener("change", () => {
        renderOperationDetail(operationDateSelect.value);
        const url = new URL(window.location.href);
        url.searchParams.set("date", operationDateSelect.value);
        window.history.replaceState({}, "", url);
    });
}

initOperationDetail();
