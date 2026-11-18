package com.ev.multiev_charging_management_system.external.weather.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(
        name = "weather_forecast_raw_data",
        uniqueConstraints = @UniqueConstraint(
                columnNames = {"source", "nx", "ny", "issued_at", "forecast_time", "category"}
        )
)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class WeatherForecastRawData {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 30)
    private String source;

    @Column(nullable = false)
    private Integer nx;

    @Column(nullable = false)
    private Integer ny;

    @Column(name = "issued_at", nullable = false)
    private LocalDateTime issuedAt;

    @Column(name = "forecast_time", nullable = false)
    private LocalDateTime forecastTime;

    @Column(nullable = false, length = 20)
    private String category;

    @Column(name = "value_text", length = 100)
    private String valueText;

    @Column(name = "value_numeric")
    private Double valueNumeric;

    @Column(length = 30)
    private String unit;

    @Column(name = "created_at", nullable = false, insertable = false, updatable = false)
    private LocalDateTime createdAt;

    @Builder
    public WeatherForecastRawData(String source, Integer nx, Integer ny,
                                  LocalDateTime issuedAt, LocalDateTime forecastTime,
                                  String category, String valueText, Double valueNumeric,
                                  String unit) {
        this.source = source;
        this.nx = nx;
        this.ny = ny;
        this.issuedAt = issuedAt;
        this.forecastTime = forecastTime;
        this.category = category;
        this.valueText = valueText;
        this.valueNumeric = valueNumeric;
        this.unit = unit;
    }
}
