package com.ev.multiev_charging_management_system.external.weather.repository;

import com.ev.multiev_charging_management_system.external.weather.entity.WeatherForecastRawData;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;

public interface WeatherForecastRawDataRepository extends JpaRepository<WeatherForecastRawData, Long> {

    List<WeatherForecastRawData> findBySourceAndNxAndNyAndIssuedAtAndForecastTimeBetweenOrderByForecastTimeAscCategoryAsc(
            String source, Integer nx, Integer ny, LocalDateTime issuedAt,
            LocalDateTime start, LocalDateTime end
    );

    boolean existsBySourceAndNxAndNyAndIssuedAtAndForecastTimeAndCategory(
            String source, Integer nx, Integer ny, LocalDateTime issuedAt,
            LocalDateTime forecastTime, String category
    );
}
