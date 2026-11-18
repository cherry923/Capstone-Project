package com.ev.multiev_charging_management_system.external.mqtt;

import com.ev.multiev_charging_management_system.external.mqtt.dto.ChargerMeasurementDto;
import com.ev.multiev_charging_management_system.mqtt.service.ChargerMessageService;
import lombok.RequiredArgsConstructor;
import tools.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.messaging.Message;
import org.springframework.stereotype.Component;
import org.springframework.integration.mqtt.support.MqttHeaders;
import java.nio.charset.StandardCharsets;

/**
 * MQTT로 수신된 충전기 메시지를 처리하는 핸들러.
 * <p>
 * external.mqtt.enabled=true인 경우에만 Bean으로 등록되며,
 * MQTT inbound adapter가 mqttInputChannel로 전달한 메시지를 받아
 * JSON payload를 ChargerMessageDto로 변환한다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(name = "external.mqtt.enabled", havingValue = "true")
public class MqttMessageHandler {

    private final ObjectMapper objectMapper;
    private final ChargerMessageService chargerMessageService;

    /**
     * mqttInputChannel로 들어온 MQTT 메시지를 처리한다.
     *
     * @param message MQTT inbound adapter가 전달한 Spring Integration 메시지.
     *                payload에는 MQTT 메시지 본문이 들어 있고,
     *                header에는 수신 topic 등의 MQTT 메타데이터가 포함된다.
     */
    @ServiceActivator(inputChannel = "mqttInputChannel")
    public void handle(Message<?> message) {
        String payload = null;
        String receivedTopic = message.getHeaders()
                .get(MqttHeaders.RECEIVED_TOPIC, String.class);

        try {
            payload = getPayloadAsString(message.getPayload());

            ChargerMeasurementDto chargerData =
                    objectMapper.readValue(payload, ChargerMeasurementDto.class);

            chargerMessageService.saveMessage(chargerData, receivedTopic);

            log.info(
                "MQTT 메시지 처리 성공. topic={}, stationId={}, chargerNo={}",
                receivedTopic,
                chargerData.getStationId(),
                chargerData.getChargerNo()
            );

        } catch (Exception e) {
            log.error(
                    "MQTT 메시지 처리 실패. topic={}, payload={}",
                    receivedTopic,
                    payload,
                    e
            );

            throw new IllegalStateException("MQTT 메시지 처리 실패", e);
        }
    }

    /**
     * MQTT payload를 문자열로 변환한다.
     * <p>
     * MQTT adapter 설정이나 broker/client 동작에 따라 payload가 byte[] 또는 String으로
     * 들어올 수 있으므로 두 타입을 모두 지원한다.
     *
     * @param payload MQTT 메시지 payload
     * @return UTF-8 문자열 payload
     * @throws IllegalArgumentException 지원하지 않는 payload 타입인 경우
     */
    private String getPayloadAsString(Object payload) {
        if (payload instanceof byte[] bytes) {
            return new String(bytes, StandardCharsets.UTF_8);
        }

        if (payload instanceof String str) {
            return str;
        }

        throw new IllegalArgumentException("지원하지 않는 MQTT payload 타입: " + payload.getClass());
    }
}
