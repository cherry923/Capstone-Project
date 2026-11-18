package com.ev.multiev_charging_management_system.external.ai.dispatch.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "ai_dispatch_run")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class AiDispatchRun {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "request_id", length = 100)
    private String requestId;

    @Column(name = "target_date")
    private LocalDate targetDate;

    @Column(nullable = false, length = 50)
    private String status;

    @Column(columnDefinition = "TEXT")
    private String message;

    @Column(name = "model_version", length = 100)
    private String modelVersion;

    @Column(name = "model_name", length = 200)
    private String modelName;

    @Column(name = "model_status", length = 100)
    private String modelStatus;

    @Column(name = "pv_source", length = 100)
    private String pvSource;

    @Column(name = "ev_source", columnDefinition = "TEXT")
    private String evSource;

    @Column(name = "team_model_source", columnDefinition = "TEXT")
    private String teamModelSource;

    @Column(name = "command_count")
    private Integer commandCount;

    @Column(name = "request_payload", nullable = false, columnDefinition = "TEXT")
    private String requestPayload;

    @Column(name = "response_payload", columnDefinition = "TEXT")
    private String responsePayload;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Builder
    public AiDispatchRun(String requestId, LocalDate targetDate, String status, String message,
                         String modelVersion, String modelName, String modelStatus,
                         String pvSource, String evSource, String teamModelSource,
                         Integer commandCount, String requestPayload, String responsePayload) {
        this.requestId = requestId;
        this.targetDate = targetDate;
        this.status = status;
        this.message = message;
        this.modelVersion = modelVersion;
        this.modelName = modelName;
        this.modelStatus = modelStatus;
        this.pvSource = pvSource;
        this.evSource = evSource;
        this.teamModelSource = teamModelSource;
        this.commandCount = commandCount;
        this.requestPayload = requestPayload;
        this.responsePayload = responsePayload;
    }

    @PrePersist
    void prePersist() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
    }
}
