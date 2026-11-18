package com.ev.multiev_charging_management_system.mqtt.repository;

import com.ev.multiev_charging_management_system.mqtt.entity.ChargerMeasurementHistory;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ChargerMeasurementRepository extends JpaRepository<ChargerMeasurementHistory, Long> {
    List<ChargerMeasurementHistory> findByIdGreaterThanOrderByIdAsc(Long afterId);

    List<ChargerMeasurementHistory> findTop11ByOrderByIdDesc();

    List<ChargerMeasurementHistory> findByStationIdAndChargerNoAndIdGreaterThanOrderByIdAsc(
            String stationId,
            Integer chargerNo,
            Long afterId
    );
}
