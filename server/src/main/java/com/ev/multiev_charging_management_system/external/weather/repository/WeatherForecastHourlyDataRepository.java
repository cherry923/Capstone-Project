package com.ev.multiev_charging_management_system.external.weather.repository;

import com.ev.multiev_charging_management_system.external.weather.entity.WeatherForecastHourlyData;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;

public interface WeatherForecastHourlyDataRepository extends JpaRepository<WeatherForecastHourlyData, Long> {

    List<WeatherForecastHourlyData> findBySourceAndNxAndNyAndIssuedAtAndForecastTimeBetweenOrderByForecastTimeAsc(
            String source, Integer nx, Integer ny, LocalDateTime issuedAt,
            LocalDateTime start, LocalDateTime end
    );

    List<WeatherForecastHourlyData> findBySourceAndNxAndNyAndForecastTimeBetweenOrderByForecastTimeAscIssuedAtDesc(
            String source, Integer nx, Integer ny, LocalDateTime start, LocalDateTime end
    );

    boolean existsBySourceAndNxAndNyAndIssuedAtAndForecastTime(
            String source, Integer nx, Integer ny, LocalDateTime issuedAt,
            LocalDateTime forecastTime
    );
}
