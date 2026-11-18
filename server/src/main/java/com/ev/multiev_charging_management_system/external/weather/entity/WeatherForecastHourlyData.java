package com.ev.multiev_charging_management_system.external.weather.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(
        name = "weather_forecast_hourly_data",
        uniqueConstraints = @UniqueConstraint(
                columnNames = {"source", "nx", "ny", "issued_at", "forecast_time"}
        )
)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class WeatherForecastHourlyData {

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

    private Double temperature;               // TMP
    private Double humidity;                  // REH
    private Double precipitationProbability;  // POP
    private Double precipitationType;         // PTY
    private Double precipitationAmount;       // PCP
    private Double snowfallAmount;            // SNO
    private Double sky;                       // SKY
    private Double windSpeed;                 // WSD
    private Double windDirection;             // VEC
    private Double eastWestWind;              // UUU
    private Double northSouthWind;            // VVV
    private Double waveHeight;                // WAV

    @Column(name = "created_at", nullable = false, insertable = false, updatable = false)
    private LocalDateTime createdAt;

    @Builder
    public WeatherForecastHourlyData(String source, Integer nx, Integer ny,
                                     LocalDateTime issuedAt, LocalDateTime forecastTime,
                                     Double temperature, Double humidity,
                                     Double precipitationProbability, Double precipitationType,
                                     Double precipitationAmount, Double snowfallAmount,
                                     Double sky, Double windSpeed, Double windDirection,
                                     Double eastWestWind, Double northSouthWind,
                                     Double waveHeight) {
        this.source = source;
        this.nx = nx;
        this.ny = ny;
        this.issuedAt = issuedAt;
        this.forecastTime = forecastTime;
        this.temperature = temperature;
        this.humidity = humidity;
        this.precipitationProbability = precipitationProbability;
        this.precipitationType = precipitationType;
        this.precipitationAmount = precipitationAmount;
        this.snowfallAmount = snowfallAmount;
        this.sky = sky;
        this.windSpeed = windSpeed;
        this.windDirection = windDirection;
        this.eastWestWind = eastWestWind;
        this.northSouthWind = northSouthWind;
        this.waveHeight = waveHeight;
    }
}
