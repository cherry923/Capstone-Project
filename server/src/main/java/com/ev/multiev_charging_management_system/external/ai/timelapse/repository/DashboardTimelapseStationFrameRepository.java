package com.ev.multiev_charging_management_system.external.ai.timelapse.repository;

import com.ev.multiev_charging_management_system.external.ai.timelapse.entity.DashboardTimelapseStationFrame;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface DashboardTimelapseStationFrameRepository extends JpaRepository<DashboardTimelapseStationFrame, Long> {

    List<DashboardTimelapseStationFrame> findByPeriodIdOrderByFrameIndexAscStationIdAsc(Long periodId);

    List<DashboardTimelapseStationFrame> findByPeriodIdAndFrameIndexOrderByStationIdAsc(Long periodId, Integer frameIndex);

    Optional<DashboardTimelapseStationFrame> findTopByPeriodIdAndStationIdAndFrameIndexLessThanOrderByFrameIndexDesc(
            Long periodId,
            String stationId,
            Integer frameIndex
    );

    void deleteByPeriodId(Long periodId);
}
