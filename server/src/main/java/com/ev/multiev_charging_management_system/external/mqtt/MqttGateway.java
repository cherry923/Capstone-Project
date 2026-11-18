package com.ev.multiev_charging_management_system.external.mqtt;

import org.springframework.integration.annotation.MessagingGateway;
import org.springframework.integration.mqtt.support.MqttHeaders;
import org.springframework.messaging.handler.annotation.Header;

/*
 * 애플리케이션 내부에서 MQTT 메시지를 발행하기 위한 Gateway 인터페이스.
 *
 * 서비스 계층에서는 MessageChannel을 직접 다루지 않고,
 * 이 인터페이스의 메서드를 호출해 MQTT outbound channel로 메시지를 전달한다.
 */
@MessagingGateway(defaultRequestChannel = "mqttOutboundChannel")
public interface MqttGateway {
    void sendToMqtt(@Header(MqttHeaders.TOPIC) String topic, String data);
}
