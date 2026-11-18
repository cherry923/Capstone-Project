package com.ev.multiev_charging_management_system.mqtt.repository;

import com.ev.multiev_charging_management_system.mqtt.entity.ChargerMeasurementFailedHistory;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChargerMeasurementFailedRepository extends JpaRepository<ChargerMeasurementFailedHistory, Long> {
}
