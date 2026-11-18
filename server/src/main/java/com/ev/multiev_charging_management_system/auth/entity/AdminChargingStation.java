package com.ev.multiev_charging_management_system.auth.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(
        name = "admin_charging_station",
        uniqueConstraints = @UniqueConstraint(columnNames = {"admin_id", "station_id"})
)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class AdminChargingStation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "admin_id", nullable = false)
    private AdminAccount admin;

    @Column(name = "station_id", nullable = false, length = 100)
    private String stationId;

    @Column(name = "station_name", nullable = false, length = 120)
    private String stationName;

    @Column(nullable = false, length = 120)
    private String region;

    @Column
    private Double latitude;

    @Column
    private Double longitude;

    @Column(nullable = false, length = 30)
    private String status;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    public static AdminChargingStation create(
            AdminAccount admin,
            String stationId,
            String stationName,
            String region,
            Double latitude,
            Double longitude,
            String status
    ) {
        AdminChargingStation station = new AdminChargingStation();
        station.admin = admin;
        station.stationId = stationId;
        station.stationName = stationName;
        station.region = region;
        station.latitude = latitude;
        station.longitude = longitude;
        station.status = status;
        return station;
    }

    @PrePersist
    void prePersist() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
    }
}
