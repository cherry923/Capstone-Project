package com.ev.multiev_charging_management_system.external.ai.timelapse.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

@Entity
@Table(
        name = "dashboard_timelapse_station_frame",
        uniqueConstraints = @UniqueConstraint(columnNames = {"period_id", "frame_index", "station_id"})
)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class DashboardTimelapseStationFrame {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "period_id", nullable = false)
    private DashboardTimelapsePeriod period;

    @Column(name = "frame_index", nullable = false)
    private Integer frameIndex;

    @Column(name = "frame_date", nullable = false)
    private LocalDate frameDate;

    @Column(name = "frame_hour", nullable = false)
    private Integer frameHour;

    @Column(name = "station_id", nullable = false, length = 100)
    private String stationId;

    @Column(name = "station_name", nullable = false, length = 120)
    private String stationName;

    @Column(nullable = false, length = 120)
    private String region;

    @Column(name = "demand_kwh", nullable = false)
    private Double demandKwh;

    @Column(name = "pv_kw", nullable = false)
    private Double pvKw;

    @Column(name = "ess_percent", nullable = false)
    private Double essPercent;

    @Column(name = "tariff_krw_per_kwh", nullable = false)
    private Double tariffKrwPerKwh;

    @Column(name = "share_energy_kwh", nullable = false)
    private Double shareEnergyKwh;

    @Column(name = "active_chargers")
    private Integer activeChargers;

    @Column(name = "total_chargers")
    private Integer totalChargers;

    @Column(name = "vehicle_count")
    private Integer vehicleCount;

    @Column(length = 30)
    private String status;

    @Column(name = "command_text", columnDefinition = "TEXT")
    private String commandText;

    @Column(name = "policy_text", columnDefinition = "TEXT")
    private String policyText;

    @Column(name = "prediction_text", columnDefinition = "TEXT")
    private String predictionText;

    public static DashboardTimelapseStationFrame create(
            DashboardTimelapsePeriod period,
            Integer frameIndex,
            LocalDate frameDate,
            Integer frameHour,
            String stationId,
            String stationName,
            String region,
            Double demandKwh,
            Double pvKw,
            Double essPercent,
            Double tariffKrwPerKwh,
            Double shareEnergyKwh,
            Integer activeChargers,
            Integer totalChargers,
            Integer vehicleCount,
            String status,
            String commandText,
            String policyText,
            String predictionText
    ) {
        DashboardTimelapseStationFrame frame = new DashboardTimelapseStationFrame();
        frame.period = period;
        frame.frameIndex = frameIndex;
        frame.frameDate = frameDate;
        frame.frameHour = frameHour;
        frame.stationId = stationId;
        frame.stationName = stationName;
        frame.region = region;
        frame.demandKwh = demandKwh;
        frame.pvKw = pvKw;
        frame.essPercent = essPercent;
        frame.tariffKrwPerKwh = tariffKrwPerKwh;
        frame.shareEnergyKwh = shareEnergyKwh;
        frame.activeChargers = activeChargers;
        frame.totalChargers = totalChargers;
        frame.vehicleCount = vehicleCount;
        frame.status = status;
        frame.commandText = commandText;
        frame.policyText = policyText;
        frame.predictionText = predictionText;
        return frame;
    }
}
