package com.ev.multiev_charging_management_system.external.weather.repository;

import com.ev.multiev_charging_management_system.external.weather.entity.PvActualHourlyData;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;

public interface PvActualHourlyDataRepository extends JpaRepository<PvActualHourlyData, Long> {

    List<PvActualHourlyData> findBySourceAndRegionAndFuelTypeAndTradeDateOrderByTradeHourAsc(
            String source, String region, String fuelType, LocalDate tradeDate
    );
}
