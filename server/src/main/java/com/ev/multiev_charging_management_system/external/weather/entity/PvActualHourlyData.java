package com.ev.multiev_charging_management_system.external.weather.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "pv_actual_hourly_data")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class PvActualHourlyData {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 60)
    private String source;

    @Column(nullable = false, length = 50)
    private String region;

    @Column(name = "fuel_type", nullable = false, length = 30)
    private String fuelType;

    @Column(name = "observed_at", nullable = false)
    private LocalDateTime observedAt;

    @Column(name = "trade_date", nullable = false)
    private LocalDate tradeDate;

    @Column(name = "trade_hour", nullable = false)
    private Integer tradeHour;

    @Column(name = "generation_mwh", nullable = false)
    private Double generationMwh;

    @Builder
    public PvActualHourlyData(String source, String region, String fuelType,
                              LocalDateTime observedAt, LocalDate tradeDate,
                              Integer tradeHour, Double generationMwh) {
        this.source = source;
        this.region = region;
        this.fuelType = fuelType;
        this.observedAt = observedAt;
        this.tradeDate = tradeDate;
        this.tradeHour = tradeHour;
        this.generationMwh = generationMwh;
    }
}
