package com.ev.multiev_charging_management_system.external.ai.timelapse.service;

import com.ev.multiev_charging_management_system.external.ai.timelapse.dto.DashboardTimelapseMqttPublishResponse;
import com.ev.multiev_charging_management_system.external.ai.timelapse.entity.DashboardTimelapsePeriod;
import com.ev.multiev_charging_management_system.external.ai.timelapse.entity.DashboardTimelapseStationFrame;
import com.ev.multiev_charging_management_system.external.ai.timelapse.repository.DashboardTimelapsePeriodRepository;
import com.ev.multiev_charging_management_system.external.ai.timelapse.repository.DashboardTimelapseStationFrameRepository;
import com.ev.multiev_charging_management_system.external.mqtt.MqttGateway;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.FORBIDDEN;
import static org.springframework.http.HttpStatus.NOT_FOUND;

@Service
@RequiredArgsConstructor
public class DashboardTimelapseMqttPublishService {

    private static final String DEMO_MODE = "demo";
    private static final String LIVE_MODE = "live";
    private static final double ESS_ACTION_EPSILON = 0.0001;

    private final DashboardTimelapsePeriodRepository periodRepository;
    private final DashboardTimelapseStationFrameRepository frameRepository;
    private final MqttGateway mqttGateway;
    private final ObjectMapper objectMapper;

    @Value("${app.dashboard.timelapse.mqtt-live-topic-enabled:false}")
    private boolean liveTopicEnabled;

    @Transactional(readOnly = true)
    public DashboardTimelapseMqttPublishResponse publishFrame(String periodKey, int frameIndex, String mode, String trigger) {
        DashboardTimelapsePeriod period = periodRepository.findByPeriodKey(periodKey)
                .orElseThrow(() -> new ResponseStatusException(NOT_FOUND, "Dashboard timelapse period not found."));
        if (frameIndex < 0) {
            throw new ResponseStatusException(BAD_REQUEST, "frame_index must be zero or greater.");
        }

        List<DashboardTimelapseStationFrame> frames =
                frameRepository.findByPeriodIdAndFrameIndexOrderByStationIdAsc(period.getId(), frameIndex);
        if (frames.isEmpty()) {
            throw new ResponseStatusException(NOT_FOUND, "Dashboard timelapse frame not found.");
        }

        String publishMode = normalizeMode(mode);
        String topicNamespace = "iot.control";
        LocalDateTime publishedAt = LocalDateTime.now();
        List<DashboardTimelapseMqttPublishResponse.PublishedCommand> commands = frames.stream()
                .map(frame -> publishStationFrame(period, frame, publishMode, topicNamespace, trigger, publishedAt))
                .toList();

        DashboardTimelapseStationFrame firstFrame = frames.get(0);
        return new DashboardTimelapseMqttPublishResponse(
                period.getPeriodKey(),
                frameIndex,
                firstFrame.getFrameDate(),
                firstFrame.getFrameHour(),
                publishMode,
                topicNamespace,
                publishedAt,
                commands
        );
    }

    private DashboardTimelapseMqttPublishResponse.PublishedCommand publishStationFrame(
            DashboardTimelapsePeriod period,
            DashboardTimelapseStationFrame frame,
            String mode,
            String topicNamespace,
            String trigger,
            LocalDateTime publishedAt
    ) {
        String stationTopicId = toStationTopicId(frame.getStationId());
        String topic = topicNamespace + "/stations/" + stationTopicId + "/commands";
        DashboardTimelapseStationFrame previousFrame =
                frameRepository.findTopByPeriodIdAndStationIdAndFrameIndexLessThanOrderByFrameIndexDesc(
                                period.getId(),
                                frame.getStationId(),
                                frame.getFrameIndex()
                        )
                        .orElse(null);
        Map<String, Object> payload = toPayload(period, frame, previousFrame, mode, trigger, publishedAt);
        mqttGateway.sendToMqtt(topic, objectMapper.writeValueAsString(payload));
        return new DashboardTimelapseMqttPublishResponse.PublishedCommand(
                stationTopicId,
                topic,
                payload
        );
    }

    private Map<String, Object> toPayload(
            DashboardTimelapsePeriod period,
            DashboardTimelapseStationFrame frame,
            DashboardTimelapseStationFrame previousFrame,
            String mode,
            String trigger,
            LocalDateTime publishedAt
    ) {
        double socAfter = toSocRatio(frame.getEssPercent());
        double socBefore = previousFrame == null ? socAfter : toSocRatio(previousFrame.getEssPercent());
        double essAction = round6(socAfter - socBefore);
        double gridTotalKwh = estimateGridTotalKwh(frame);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("command_source", "dashboard_timelapse");
        payload.put("mode", mode);
        payload.put("demo", !LIVE_MODE.equals(mode));
        payload.put("trigger", trigger == null || trigger.isBlank() ? "dashboard" : trigger.trim());
        payload.put("period_key", period.getPeriodKey());
        payload.put("frame_index", frame.getFrameIndex());
        payload.put("frame_date", frame.getFrameDate().toString());
        payload.put("hour", frame.getFrameHour());
        payload.put("published_at", publishedAt.toString());
        payload.put("station_id", toStationTopicId(frame.getStationId()));
        payload.put("source_station_id", frame.getStationId());
        payload.put("station_name", frame.getStationName());
        payload.put("demand_kwh", frame.getDemandKwh());
        payload.put("pv_kw", frame.getPvKw());
        payload.put("tariff_krw_per_kwh", frame.getTariffKrwPerKwh());
        payload.put("share_energy_kwh", frame.getShareEnergyKwh());
        payload.put("ess_action", essAction);
        payload.put("raw_ess_action", essAction);
        payload.put("pv_priority", 1.0);
        payload.put("soc_before", round6(socBefore));
        payload.put("soc_after", round6(socAfter));
        payload.put("grid_total_kwh", gridTotalKwh);
        payload.put("grid_cost", round2(gridTotalKwh * frame.getTariffKrwPerKwh()));
        payload.put("ess_percent", frame.getEssPercent());
        payload.put("command", toEssCommand(essAction));
        payload.put("display_command", frame.getCommandText());
        payload.put("safety_adjusted", false);
        payload.put("policy_text", frame.getPolicyText());
        payload.put("prediction_text", frame.getPredictionText());
        return payload;
    }

    private String toStationTopicId(String stationId) {
        String trimmed = stationId == null ? "" : stationId.trim();
        if (trimmed.matches("\\d+")) {
            return "ST" + String.format(Locale.ROOT, "%03d", Integer.parseInt(trimmed));
        }
        return trimmed.toUpperCase(Locale.ROOT);
    }

    private double toSocRatio(Double essPercent) {
        if (essPercent == null) {
            return 0.0;
        }
        return essPercent / 100.0;
    }

    private double estimateGridTotalKwh(DashboardTimelapseStationFrame frame) {
        double demandKwh = frame.getDemandKwh() == null ? 0.0 : frame.getDemandKwh();
        double pvKw = frame.getPvKw() == null ? 0.0 : frame.getPvKw();
        double shareEnergyKwh = frame.getShareEnergyKwh() == null ? 0.0 : frame.getShareEnergyKwh();
        return round2(Math.max(0.0, demandKwh - pvKw - shareEnergyKwh));
    }

    private String toEssCommand(double essAction) {
        if (essAction > ESS_ACTION_EPSILON) {
            return "charge_ess:dashboard_timelapse";
        }
        if (essAction < -ESS_ACTION_EPSILON) {
            return "discharge_ess:dashboard_timelapse";
        }
        return "hold_ess:dashboard_timelapse";
    }

    private double round6(double value) {
        return Math.round(value * 1_000_000.0) / 1_000_000.0;
    }

    private double round2(double value) {
        return Math.round(value * 100.0) / 100.0;
    }

    private String normalizeMode(String mode) {
        if (mode == null || mode.isBlank()) {
            return DEMO_MODE;
        }
        String normalized = mode.trim().toLowerCase(Locale.ROOT);
        if (DEMO_MODE.equals(normalized) || LIVE_MODE.equals(normalized)) {
            if (LIVE_MODE.equals(normalized) && !liveTopicEnabled) {
                throw new ResponseStatusException(FORBIDDEN, "Live MQTT publish is disabled.");
            }
            return normalized;
        }
        throw new ResponseStatusException(BAD_REQUEST, "mode must be demo or live.");
    }
}
