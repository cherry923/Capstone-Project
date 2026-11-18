package com.ev.multiev_charging_management_system.external.ai.timelapse.repository;

import com.ev.multiev_charging_management_system.external.ai.timelapse.entity.DashboardTimelapsePeriod;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface DashboardTimelapsePeriodRepository extends JpaRepository<DashboardTimelapsePeriod, Long> {

    boolean existsByPeriodKey(String periodKey);

    Optional<DashboardTimelapsePeriod> findByPeriodKey(String periodKey);

    Optional<DashboardTimelapsePeriod> findTopByActiveTrueOrderByEndDateDescCreatedAtDesc();

    List<DashboardTimelapsePeriod> findByActiveTrueOrderByEndDateDescCreatedAtDesc();
}
