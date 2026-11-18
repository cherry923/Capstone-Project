package com.ev.multiev_charging_management_system.external.weather.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(
        name = "weather_raw_data",
        uniqueConstraints = @UniqueConstraint(
                columnNames = {"asos_station_id", "observation_time"}
        )
)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class WeatherRawData {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "asos_station_id", nullable = false)
    private Integer asosStationId;

    @Column(name = "observation_time", nullable = false)
    private LocalDateTime observationTime;

    @Column(name = "station_name")
    private String stationName;

    private Double temperature;      // 기온 (°C) — ASOS: ta
    private Double rainfall;         // 강수량 (mm) — ASOS: rn
    private Double humidity;         // 습도 (%) — ASOS: hm
    private Double snowfall;         // 적설 (cm) — ASOS: dsnw
    private Double cloudCover;       // 전운량 (10분위) — ASOS: dc10Tca
    private Double sunshineDuration; // 일조시간 (hr) — ASOS: ss
    private Double solarRadiation;   // 일사량 (MJ/m²) — ASOS: icsr
    private Double windSpeed;        // 풍속 (m/s) — ASOS: ws
    private Integer windDirection;   // 풍향 (16방위) — ASOS: wd

    @Builder
    public WeatherRawData(Integer asosStationId, LocalDateTime observationTime,
                          String stationName, Double temperature, Double rainfall,
                          Double humidity, Double snowfall, Double cloudCover,
                          Double sunshineDuration, Double solarRadiation,
                          Double windSpeed, Integer windDirection) {
        this.asosStationId = asosStationId;
        this.observationTime = observationTime;
        this.stationName = stationName;
        this.temperature = temperature;
        this.rainfall = rainfall;
        this.humidity = humidity;
        this.snowfall = snowfall;
        this.cloudCover = cloudCover;
        this.sunshineDuration = sunshineDuration;
        this.solarRadiation = solarRadiation;
        this.windSpeed = windSpeed;
        this.windDirection = windDirection;
    }
}
