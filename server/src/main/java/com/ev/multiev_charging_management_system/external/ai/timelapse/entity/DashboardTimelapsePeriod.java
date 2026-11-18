package com.ev.multiev_charging_management_system.external.ai.timelapse.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(
        name = "dashboard_timelapse_period",
        uniqueConstraints = @UniqueConstraint(columnNames = "period_key")
)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class DashboardTimelapsePeriod {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "period_key", nullable = false, length = 100)
    private String periodKey;

    @Column(nullable = false, length = 160)
    private String label;

    @Column(name = "start_date", nullable = false)
    private LocalDate startDate;

    @Column(name = "end_date", nullable = false)
    private LocalDate endDate;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(length = 120)
    private String source;

    @Column(name = "is_active", nullable = false)
    private boolean active;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public static DashboardTimelapsePeriod create(
            String periodKey,
            String label,
            LocalDate startDate,
            LocalDate endDate,
            String description,
            String source,
            boolean active
    ) {
        DashboardTimelapsePeriod period = new DashboardTimelapsePeriod();
        period.update(periodKey, label, startDate, endDate, description, source, active);
        return period;
    }

    public void update(
            String periodKey,
            String label,
            LocalDate startDate,
            LocalDate endDate,
            String description,
            String source,
            boolean active
    ) {
        this.periodKey = periodKey;
        this.label = label;
        this.startDate = startDate;
        this.endDate = endDate;
        this.description = description;
        this.source = source;
        this.active = active;
    }

    @PrePersist
    void prePersist() {
        LocalDateTime now = LocalDateTime.now();
        if (createdAt == null) {
            createdAt = now;
        }
        if (updatedAt == null) {
            updatedAt = now;
        }
    }

    @PreUpdate
    void preUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
