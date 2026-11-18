package com.ev.multiev_charging_management_system.mqtt.entity;

import com.ev.multiev_charging_management_system.external.mqtt.dto.ChargerMeasurementDto;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Column;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;

@Entity
@Table(
        name = "charger_measurement",
        indexes = {
                @Index(
                        name = "idx_station_charger_time",
                        columnList = "station_id, charger_no, measured_at"
                ),
                @Index(
                        name = "idx_measured_at",
                        columnList = "measured_at"
                )
        }
)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ChargerMeasurementHistory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "station_id", nullable = false, length = 100)
    private String stationId;

    @Column(name = "charger_no", nullable = false)
    private Integer chargerNo;

    @Column(name = "charging", nullable = false)
    private boolean charging;

    @Column(name = "power")
    private Integer power;

    @Column(name = "voltage")
    private Double voltage;

    @Column(name = "current")
    private Double current;

    @Column(name = "ess_remain")
    private Double essRemain;

    @Column(name = "measured_at", nullable = false)
    private LocalDateTime measuredAt;

    @Column(name = "received_at", nullable = false)
    private LocalDateTime receivedAt;

    @Column(name = "topic", length = 255)
    private String topic;

    public static ChargerMeasurementHistory from(
            ChargerMeasurementDto dto,
            String topic
    ) {
        ChargerMeasurementHistory entity = new ChargerMeasurementHistory();

        entity.stationId = dto.getStationId();
        entity.chargerNo = dto.getChargerNo();
        entity.charging = dto.isCharging();
        entity.power = dto.getPower();
        entity.voltage = dto.getVoltage();
        entity.current = dto.getCurrent();
        entity.essRemain = dto.getEssRemain();

        entity.measuredAt = convertTimestamp(dto.getTimestamp());

        entity.receivedAt = LocalDateTime.now();
        entity.topic = topic;

        return entity;
    }

    public static ChargerMeasurementHistory virtual(
            String stationId,
            Integer chargerNo,
            boolean charging,
            Integer power,
            Double voltage,
            Double current,
            Double essRemain,
            String topic
    ) {
        ChargerMeasurementHistory entity = new ChargerMeasurementHistory();

        entity.stationId = stationId;
        entity.chargerNo = chargerNo;
        entity.charging = charging;
        entity.power = power;
        entity.voltage = voltage;
        entity.current = current;
        entity.essRemain = essRemain;

        entity.measuredAt = LocalDateTime.now();
        entity.receivedAt = LocalDateTime.now();

        entity.topic = topic;

        return entity;
    }

    private static LocalDateTime convertTimestamp(Long timestamp) {
        if (timestamp == null) {
            return LocalDateTime.now();
        }

        return Instant.ofEpochMilli(timestamp)
                .atZone(ZoneId.systemDefault())
                .toLocalDateTime();
    }
}