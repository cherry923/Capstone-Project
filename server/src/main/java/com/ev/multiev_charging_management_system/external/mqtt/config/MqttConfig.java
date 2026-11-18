package com.ev.multiev_charging_management_system.external.mqtt.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.MessageChannel;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.integration.channel.DirectChannel;
import org.springframework.integration.core.MessageProducer;
import org.springframework.integration.mqtt.inbound.Mqttv5PahoMessageDrivenChannelAdapter;
import org.springframework.integration.mqtt.outbound.Mqttv5PahoMessageHandler;
import org.springframework.messaging.MessageHandler;

@Configuration
@EnableConfigurationProperties(MqttProperties.class)
@ConditionalOnProperty(name = "external.mqtt.enabled", havingValue = "true")
public class MqttConfig {

    /*
     * external.mqtt 하위 설정값을 바인딩한 프로퍼티 객체.
     * broker-url, inbound client-id/topic, outbound client-id/default-topic 등을
     * 이 객체를 통해 참조한다.
     */
    private final MqttProperties mqttProperties;

    public MqttConfig(MqttProperties mqttProperties) {
        this.mqttProperties = mqttProperties;
    }

    /*
     * MQTT inbound adapter가 수신한 메시지를 애플리케이션 내부로 전달하는 입력 채널.
     * MqttMessageHandler의 @ServiceActivator(inputChannel = "mqtt5InputChannel")와
     * 연결되어, 이 채널로 들어온 MQTT 메시지가 핸들러 메서드로 전달된다.
     */
    @Bean
    public MessageChannel mqttInputChannel() {
        return new DirectChannel();
    }

    /*
     * MQTT inbound adapter.
     * broker-url로 MQTT broker에 연결하고, inbound.client-id를 client id로 사용하며,
     * inbound.topic을 구독한다.
     * 수신한 메시지는 payload를 String 타입으로 변환한 뒤 mqtt5InputChannel로 전달한다.
     */
    @Bean
    public MessageProducer mqttInbound() {
        Mqttv5PahoMessageDrivenChannelAdapter adapter =
                new Mqttv5PahoMessageDrivenChannelAdapter(
                        mqttProperties.getBrokerUrl(),
                        mqttProperties.getInbound().getClientId(),
                        mqttProperties.getInbound().getTopic()
                );

        adapter.setCompletionTimeout(5000);
        adapter.setQos(1);
        adapter.setPayloadType(String.class);
        adapter.setOutputChannel(mqttInputChannel());

        return adapter;
    }

    /*
     * 애플리케이션 내부에서 MQTT broker로 발행할 메시지를 전달하는 출력 채널.
     *
     * 이 채널로 메시지를 보내면 mqtt5Outbound handler가 받아 MQTT broker로 publish한다.
     */
    @Bean
    public MessageChannel mqttOutboundChannel() {
        return new DirectChannel();
    }

    /*
     * MQTT outbound message handler.
     *
     * @ServiceActivator를 통해 mqtt5OutboundChannel에 연결되며,
     * 해당 채널로 들어온 메시지를 MQTT broker로 publish한다.
     */
    @Bean
    @ServiceActivator(inputChannel = "mqttOutboundChannel")
    public MessageHandler mqttOutbound() {
        Mqttv5PahoMessageHandler messageHandler =
                new Mqttv5PahoMessageHandler(
                        mqttProperties.getBrokerUrl(),
                        mqttProperties.getOutbound().getClientId()
                );

        messageHandler.setDefaultQos(1);
        messageHandler.setAsync(true);
        messageHandler.setDefaultTopic(mqttProperties.getOutbound().getDefaultTopic());

        return messageHandler;
    }
}