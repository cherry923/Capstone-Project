package com.ev.multiev_charging_management_system.external.ai.dispatch.entity;

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
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(
        name = "ai_dispatch_command",
        uniqueConstraints = @UniqueConstraint(
                columnNames = {"dispatch_run_id", "command_index"}
        )
)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class AiDispatchCommand {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "dispatch_run_id", nullable = false)
    private AiDispatchRun dispatchRun;

    @Column(name = "command_index", nullable = false)
    private Integer commandIndex;

    @Column(name = "dispatch_hour")
    private Integer hour;

    @Column(name = "station_id", length = 100)
    private String stationId;

    @Column(name = "share_energy_kwh")
    private Double shareEnergyKwh;

    @Column(name = "ess_action")
    private Double essAction;

    @Column(name = "raw_ess_action")
    private Double rawEssAction;

    @Column(name = "pv_priority")
    private Double pvPriority;

    @Column(name = "soc_before")
    private Double socBefore;

    @Column(name = "soc_after")
    private Double socAfter;

    @Column(name = "grid_total_kwh")
    private Double gridTotalKwh;

    @Column(name = "grid_cost")
    private Double gridCost;

    @Column(length = 100)
    private String command;

    @Column(name = "safety_adjusted")
    private Boolean safetyAdjusted;

    @Column(name = "command_payload", nullable = false, columnDefinition = "TEXT")
    private String commandPayload;

    @Builder
    public AiDispatchCommand(AiDispatchRun dispatchRun, Integer commandIndex, Integer hour, String stationId,
                             Double shareEnergyKwh, Double essAction, Double rawEssAction,
                             Double pvPriority, Double socBefore, Double socAfter,
                             Double gridTotalKwh, Double gridCost, String command,
                             Boolean safetyAdjusted, String commandPayload) {
        this.dispatchRun = dispatchRun;
        this.commandIndex = commandIndex;
        this.hour = hour;
        this.stationId = stationId;
        this.shareEnergyKwh = shareEnergyKwh;
        this.essAction = essAction;
        this.rawEssAction = rawEssAction;
        this.pvPriority = pvPriority;
        this.socBefore = socBefore;
        this.socAfter = socAfter;
        this.gridTotalKwh = gridTotalKwh;
        this.gridCost = gridCost;
        this.command = command;
        this.safetyAdjusted = safetyAdjusted;
        this.commandPayload = commandPayload;
    }
}
