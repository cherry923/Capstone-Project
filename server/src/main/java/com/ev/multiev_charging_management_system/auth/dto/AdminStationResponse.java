package com.ev.multiev_charging_management_system.auth.dto;

import com.ev.multiev_charging_management_system.auth.entity.AdminChargingStation;

public record AdminStationResponse(
        String stationId,
        String stationName,
        String region,
        Double latitude,
        Double longitude,
        String status
) {
    public static AdminStationResponse from(AdminChargingStation station) {
        return new AdminStationResponse(
                station.getStationId(),
                station.getStationName(),
                station.getRegion(),
                station.getLatitude(),
                station.getLongitude(),
                station.getStatus()
        );
    }
}
