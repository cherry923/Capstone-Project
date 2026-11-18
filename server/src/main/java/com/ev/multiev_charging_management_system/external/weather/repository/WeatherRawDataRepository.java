package com.ev.multiev_charging_management_system.external.weather.repository;

import com.ev.multiev_charging_management_system.external.weather.entity.WeatherRawData;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;

public interface WeatherRawDataRepository extends JpaRepository<WeatherRawData, Long> {

    List<WeatherRawData> findByAsosStationIdAndObservationTimeBetweenOrderByObservationTimeAsc(
            Integer asosStationId, LocalDateTime start, LocalDateTime end
    );

    boolean existsByAsosStationIdAndObservationTime(
            Integer asosStationId, LocalDateTime observationTime
    );
}
