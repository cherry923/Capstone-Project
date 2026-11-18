package com.ev.multiev_charging_management_system.external.mqtt.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Getter
@Setter
@ConfigurationProperties(prefix = "external.mqtt")
public class MqttProperties {

    private boolean enabled = false;
    private String brokerUrl;
    private String username;
    private String password;

    private Inbound inbound = new Inbound();
    private Outbound outbound = new Outbound();

    @Getter
    @Setter
    public static class Inbound {
        private String clientId = "local-inbound-client";
        private String topic = "test/inbound";
    }

    @Getter
    @Setter
    public static class Outbound {
        private String clientId = "local-outbound-client";
        private String defaultTopic = "test/outbound";
    }
}
