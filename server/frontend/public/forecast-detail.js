const forecastComparisonDataUrl = "assets/operation-comparison/evonly_vmoderate_v2p90_pvess_multiseed.json";
const forecastDateSelect = document.getElementById("forecast-date-select");
const forecastMetricGrid = document.getElementById("forecast-metric-grid");
const forecastPvChart = document.getElementById("forecast-pv-chart");
const forecastStationChart = document.getElementById("forecast-station-chart");
const forecastPvDateChip = document.getElementById("forecast-pv-date-chip");
let forecastComparisonData = window.operationComparisonData || null;
const forecastMsPerDay = 24 * 60 * 60 * 1000;
const forecastWeekdays = ["일", "월", "화", "수", "목", "금", "토"];
const forecastStationDisplayNames = new Map([
    ["1", "강남 허브"],
    ["2", "마포 스테이션"],
    ["3", "송파 에너지 파크"],
    ["ST001", "강남 허브"],
    ["ST002", "마포 스테이션"],
    ["ST003", "송파 에너지 파크"]
]);
function forecastFormatKwh(value) {
    return `${Math.round(Number(value)).toLocaleString("ko-KR")}kWh`;
}
function forecastDateFromString(date) {
    return new Date(`${date}T00:00:00Z`);
}
function forecastDateToString(date) {
    return date.toISOString().slice(0, 10);
}
function forecastFormatMonthDay(date) {
    const [, month, day] = date.split("-");
    return `${Number(month)}월 ${Number(day)}일`;
}
function forecastFormatWeekTick(date) {
    const parsed = forecastDateFromString(date);
    const [, month, day] = date.split("-");
    return `${Number(month)}/${Number(day)} ${forecastWeekdays[parsed.getUTCDay()]}`;
}
function forecastFormatWeekLabel(week) {
    return `${forecastFormatMonthDay(week.startDate)}-${forecastFormatMonthDay(week.endDate)}`;
}
function forecastWeekStartDate(date) {
    const parsed = forecastDateFromString(date);
    const day = parsed.getUTCDay();
    const mondayOffset = (day + 6) % 7;
    return forecastDateToString(new Date(parsed.getTime() - mondayOffset * forecastMsPerDay));
}
function getForecastStationKey(station) {
    const rawStation = String(station.station ?? station.stationId ?? station.station_id ?? station.id ?? station.label ?? "").trim();
    return rawStation.replace(/^ST0*/i, "") || rawStation;
}
function forecastStationDisplayLabel(station) {
    const rawStation = String(station.station ?? station.stationId ?? station.station_id ?? station.id ?? "").trim();
    const normalizedStation = rawStation.replace(/^ST0*/i, "");
    return forecastStationDisplayNames.get(rawStation.toUpperCase())
        || forecastStationDisplayNames.get(normalizedStation)
        || station.label
        || rawStation;
}
function forecastLineBounds(series) {
    const values = series.flatMap((item) => item.values).filter((value) => Number.isFinite(value));
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 1);
    const padding = Math.max((max - min) * 0.12, 1);
    return { min: Math.max(0, min - padding), max: max + padding };
}
function forecastPolyline(values, bounds, width = 680, height = 280) {
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
function forecastChart(series, ticks, ariaLabel) {
    const pointCount = Math.max(...series.map((item) => item.values.length), 1);
    const width = Math.max(680, (pointCount - 1) * 8 + 68);
    const height = 280;
    const bounds = forecastLineBounds(series);
    const grid = [0, 1, 2, 3].map((row) => {
        const y = 22 + ((height - 64) * row) / 3;
        return `<line x1="48" x2="${width - 20}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}"></line>`;
    }).join("");
    const lines = series.map((item) => `
      <polyline
        points="${forecastPolyline(item.values, bounds, width, height)}"
        fill="none"
        stroke="${item.color}"
        stroke-width="${item.width || 4}"
        ${item.dashArray ? `stroke-dasharray="${item.dashArray}"` : ""}
        stroke-linecap="round"
        stroke-linejoin="round"
        opacity="${item.opacity ?? 1}"
      ></polyline>
    `).join("");
    const tickMarkup = ticks.map((tick) => {
        const x = 48 + ((width - 68) * tick.index) / Math.max(pointCount - 1, 1);
        return `<span style="left:${(x / width * 100).toFixed(2)}%">${tick.label}</span>`;
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
        <svg class="operation-svg" viewBox="0 0 ${width} ${height}" style="min-width:${width}px" role="img" aria-label="${ariaLabel}">
          <g class="operation-svg-grid">${grid}</g>
          ${lines}
        </svg>
        <div class="operation-axis-labels" style="min-width:${width}px">${tickMarkup}</div>
      </div>
      <div class="operation-legend">${legend}</div>
    `;
}
function getForecastWeeks(data) {
    const groups = new Map();
    data.days.forEach((day) => {
        const key = forecastWeekStartDate(day.date);
        if (!groups.has(key)) {
            groups.set(key, { key, startDate: day.date, endDate: day.date, days: [] });
        }
        const week = groups.get(key);
        week.days.push(day);
        week.startDate = week.days[0].date;
        week.endDate = week.days[week.days.length - 1].date;
    });
    return Array.from(groups.values());
}
function getForecastWeekFromUrl(data, weeks) {
    const params = new URLSearchParams(window.location.search);
    const requestedWeek = params.get("week");
    const weekByKey = weeks.find((week) => week.key === requestedWeek);
    if (weekByKey)
        return weekByKey;
    const requestedDate = params.get("date") || data.meta.recommendedDate || data.days[0]?.date;
    return weeks.find((week) => week.days.some((day) => day.date === requestedDate)) || weeks[0];
}
function getForecastWeek(weeks, weekKey) {
    return weeks.find((week) => week.key === weekKey) || weeks[0];
}
function renderForecastWeekOptions(weeks, selectedWeek) {
    if (!forecastDateSelect)
        return;
    forecastDateSelect.innerHTML = weeks
        .map((week) => `<option value="${week.key}" ${week.key === selectedWeek.key ? "selected" : ""}>${forecastFormatWeekLabel(week)}</option>`)
        .join("");
}
function renderForecastMetrics(data) {
    if (!forecastMetricGrid)
        return;
    forecastMetricGrid.innerHTML = data.forecastMetrics.map((metric) => `
      <article class="forecast-metric-card">
        <span>${metric.label}</span>
        <strong>${metric.value}${metric.unit}</strong>
        <p>${metric.note}</p>
      </article>
    `).join("");
}
function forecastWeekTicks(week) {
    return week.days.map((day, index) => ({
        label: forecastFormatWeekTick(day.date),
        index: index * 24
    }));
}
function forecastWeekHours(week) {
    return week.days.flatMap((day) => day.hours);
}
function forecastWeekStationSeries(week) {
    const stations = new Map();
    week.days.forEach((day) => {
        (day.stationDemandHours || []).forEach((station) => {
            const key = getForecastStationKey(station);
            if (!stations.has(key)) {
                stations.set(key, {
                    station,
                    actual: [],
                    forecast: []
                });
            }
            const stationSeries = stations.get(key);
            stationSeries.actual.push(...station.values);
            stationSeries.forecast.push(...(station.forecastValues || station.values));
        });
    });
    return Array.from(stations.values());
}
function renderForecastCharts(week) {
    const ticks = forecastWeekTicks(week);
    const weekHours = forecastWeekHours(week);
    const weekLabel = forecastFormatWeekLabel(week);
    if (forecastPvDateChip)
        forecastPvDateChip.textContent = weekLabel;
    if (forecastPvChart) {
        forecastPvChart.innerHTML = forecastChart([
            { label: "PV 실제", color: "#0aa99a", values: weekHours.map((hour) => hour.pvActual), width: 5 },
            { label: "PV 예측", color: "#7bbf5b", values: weekHours.map((hour) => hour.pvForecast), width: 4, opacity: 0.8, dashArray: "7 7" }
        ], ticks, `${weekLabel} PV 실제 예측 그래프`);
    }
    if (forecastStationChart) {
        const series = forecastWeekStationSeries(week).flatMap((stationSeries) => {
            const label = forecastStationDisplayLabel(stationSeries.station);
            return [
                {
                    label: `${label} 실제`,
                    color: stationSeries.station.color,
                    values: stationSeries.actual,
                    width: stationSeries.station.station === "2" ? 5 : 4
                },
                {
                    label: `${label} 예측`,
                    color: stationSeries.station.color,
                    values: stationSeries.forecast,
                    width: stationSeries.station.station === "2" ? 4 : 3,
                    opacity: 0.72,
                    dashArray: "7 7"
                }
            ];
        });
        forecastStationChart.innerHTML = forecastChart(series, ticks, `${weekLabel} 충전소별 EV 실제 예측 수요 그래프`);
    }
}
function renderForecastDetail(week) {
    const data = forecastComparisonData;
    if (!week)
        return;
    renderForecastMetrics(data);
    renderForecastCharts(week);
}
async function initForecastDetail() {
    if (!forecastDateSelect || !forecastMetricGrid)
        return;
    if (!forecastComparisonData) {
        try {
            const response = await fetch(forecastComparisonDataUrl);
            forecastComparisonData = await response.json();
        }
        catch (error) {
            forecastMetricGrid.innerHTML = `<article class="forecast-metric-card"><span>데이터 오류</span><strong>불러오기 실패</strong><p>예측 비교 데이터를 다시 불러와 주세요.</p></article>`;
            console.warn("Forecast comparison data fetch failed", error);
            return;
        }
    }
    const weeks = getForecastWeeks(forecastComparisonData);
    const selectedWeek = getForecastWeekFromUrl(forecastComparisonData, weeks);
    renderForecastWeekOptions(weeks, selectedWeek);
    renderForecastDetail(selectedWeek);
    forecastDateSelect.addEventListener("change", () => {
        const week = getForecastWeek(weeks, forecastDateSelect.value);
        renderForecastDetail(week);
        const url = new URL(window.location.href);
        url.searchParams.set("week", week.key);
        url.searchParams.delete("date");
        window.history.replaceState({}, "", url);
    });
}
initForecastDetail();
