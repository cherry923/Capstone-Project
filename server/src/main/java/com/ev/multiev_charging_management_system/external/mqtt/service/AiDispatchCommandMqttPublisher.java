package com.ev.multiev_charging_management_system.external.mqtt.service;

import com.ev.multiev_charging_management_system.external.ai.dispatch.entity.AiDispatchCommand;
import com.ev.multiev_charging_management_system.external.mqtt.MqttGateway;
import com.ev.multiev_charging_management_system.mqtt.service.VirtualStationEssStateService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import tools.jackson.databind.ObjectMapper;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * AI 제어 명령을 MQTT 토픽으로 발행하는 서비스 객체.
 * <p>
 * 각 충전소별 제어 명령을 MQTT payload로 변환한 뒤
 * {@code iot.control/stations/{stationId}/commands} 토픽으로 전송한다.
 * 명령 발행 후에 가상 충전소의 ESS 잔여 SOC 상태도 함께 갱신한다.
 */
@Service
@RequiredArgsConstructor
public class AiDispatchCommandMqttPublisher {

    private final MqttGateway mqttGateway;
    private final VirtualStationEssStateService virtualStationEssStateService;
    private final ObjectMapper objectMapper;

    /**
     * AI 제어명령 목록을 충전소별 MQTT 제어 토픽으로 발행한다.
     *
     * @param commands AI 서버 또는 저장소에서 생성된 충전소별 제어명령 목록
     */
    public void publish(List<AiDispatchCommand> commands) {
        for (AiDispatchCommand command : commands) {
            String topic = "iot.control/stations/" + command.getStationId() + "/commands";
            String payload = objectMapper.writeValueAsString(toPayload(command));

            mqttGateway.sendToMqtt(topic, payload);

            virtualStationEssStateService.updateEssRemain(
                    command.getStationId(),
                    command.getSocAfter()
            );
        }
    }

    /**
     * AI 제어 명령 엔티티를 MQTT로 전송할 JSON payload 형태로 변환한다.
     *
     * @param command 단일 충전소에 대한 AI 디스패치 명령
     * @return MQTT 메시지 본문으로 직렬화할 payload 맵
     */
    private Map<String, Object> toPayload(AiDispatchCommand command) {
        Map<String, Object> payload = new LinkedHashMap<>();

        payload.put("station_id", command.getStationId());
        payload.put("hour", command.getHour());
        payload.put("share_energy_kwh", command.getShareEnergyKwh());
        payload.put("ess_action", command.getEssAction());
        payload.put("raw_ess_action", command.getRawEssAction());
        payload.put("pv_priority", command.getPvPriority());
        payload.put("soc_before", command.getSocBefore());
        payload.put("soc_after", command.getSocAfter());
        payload.put("grid_total_kwh", command.getGridTotalKwh());
        payload.put("grid_cost", command.getGridCost());
        payload.put("command", command.getCommand());
        payload.put("safety_adjusted", command.getSafetyAdjusted());

        return payload;
    }
}
