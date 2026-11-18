package com.ev.multiev_charging_management_system.mqtt.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "mqtt_failed_message")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ChargerMeasurementFailedHistory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String topic;

    private String payload;

    private String errorMessage;

    private LocalDateTime failedAt;

    public static ChargerMeasurementFailedHistory of(
            String topic,
            String payload,
            Exception e
    ) {
        ChargerMeasurementFailedHistory entity = new ChargerMeasurementFailedHistory();
        entity.topic = topic;
        entity.payload = payload;
        entity.errorMessage = e.getMessage();
        entity.failedAt = LocalDateTime.now();
        return entity;
    }
}
