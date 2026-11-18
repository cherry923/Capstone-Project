package com.ev.multiev_charging_management_system.mqtt.dto;

import com.ev.multiev_charging_management_system.mqtt.entity.ChargerMeasurementHistory;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChargerMeasurementResponse {

    private Long id;
    private String stationId;
    private Integer chargerNo;
    private boolean charging;
    private Integer power;
    private Double voltage;
    private Double current;
    private Double essRemain;
    private Long measuredTimestamp;
    private LocalDateTime measuredAt;
    private LocalDateTime receivedAt;

    public static ChargerMeasurementResponse from(
            ChargerMeasurementHistory chargerMeasurementHistory
    ) {
        return ChargerMeasurementResponse.builder()
                .id(chargerMeasurementHistory.getId())
                .stationId(chargerMeasurementHistory.getStationId())
                .chargerNo(chargerMeasurementHistory.getChargerNo())
                .charging(chargerMeasurementHistory.isCharging())
                .power(chargerMeasurementHistory.getPower())
                .voltage(chargerMeasurementHistory.getVoltage())
                .current(chargerMeasurementHistory.getCurrent())
                .essRemain(chargerMeasurementHistory.getEssRemain())
                .measuredAt(chargerMeasurementHistory.getMeasuredAt())
                .receivedAt(chargerMeasurementHistory.getReceivedAt())
                .build();
    }
}
