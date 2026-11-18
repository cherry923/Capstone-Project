package com.ev.multiev_charging_management_system.external.mqtt.dto;

import lombok.Getter;

@Getter
public class ChargerMeasurementDto {
    private String stationId;
    private Integer chargerNo;
    private boolean charging;
    private Integer power;
    private Long timestamp;
    private Double voltage;
    private Double current;

    private Double essRemain;
}
