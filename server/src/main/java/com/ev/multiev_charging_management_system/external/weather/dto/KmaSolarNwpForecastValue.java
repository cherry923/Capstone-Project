package com.ev.multiev_charging_management_system.external.weather.dto;

import java.time.LocalDateTime;

public record KmaSolarNwpForecastValue(
        LocalDateTime issuedAtUtc,
        LocalDateTime forecastTimeUtc,
        String variable,
        Double longitude,
        Double latitude,
        Double value
) {
}
