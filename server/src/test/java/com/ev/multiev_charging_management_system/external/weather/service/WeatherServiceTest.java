package com.ev.multiev_charging_management_system.external.weather.service;

import com.ev.multiev_charging_management_system.external.ai.dto.PvPredictionRequest;
import com.ev.multiev_charging_management_system.external.weather.entity.PvActualHourlyData;
import com.ev.multiev_charging_management_system.external.weather.entity.WeatherRawData;
import com.ev.multiev_charging_management_system.external.weather.repository.PvActualHourlyDataRepository;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.stream.IntStream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class WeatherServiceTest {

    private final WeatherService weatherService = new WeatherService(null, null, null);

    @Test
    void toEncoderWeather168hSortsAndKeepsLatest168Hours() {
        LocalDateTime start = LocalDateTime.of(2026, 4, 29, 0, 0);
        List<WeatherRawData> rawData = new ArrayList<>(IntStream.range(0, 170)
                .mapToObj(index -> weatherRow(start.plusHours(index), (double) index))
                .toList());
        Collections.reverse(rawData);

        List<PvPredictionRequest.WeatherHourly> result = weatherService.toEncoderWeather168h(rawData);

        assertEquals(168, result.size());
        assertEquals(2.0, result.get(0).getTemperature());
        assertEquals(169.0, result.get(result.size() - 1).getTemperature());
        assertEquals(2, result.get(0).getHour());
        assertEquals(1, result.get(result.size() - 1).getHour());
    }

    @Test
    void toEncoderWeatherMapsMissingWeatherValuesToZero() {
        LocalDateTime observationTime = LocalDateTime.of(2026, 5, 6, 15, 0);

        List<PvPredictionRequest.WeatherHourly> result = weatherService.toEncoderWeather(List.of(
                WeatherRawData.builder()
                        .asosStationId(112)
                        .observationTime(observationTime)
                        .temperature(null)
                        .rainfall(null)
                        .humidity(null)
                        .snowfall(null)
                        .cloudCover(null)
                        .sunshineDuration(null)
                        .solarRadiation(null)
                        .build()
        ));

        PvPredictionRequest.WeatherHourly row = result.get(0);
        assertEquals(15, row.getHour());
        assertEquals(0.0, row.getTemperature());
        assertEquals(0.0, row.getRain());
        assertEquals(0.0, row.getHumidity());
        assertEquals(0.0, row.getSnow());
        assertEquals(0.0, row.getCloud());
        assertEquals(0.0, row.getDuration());
        assertEquals(0.0, row.getRadiation());
        assertEquals(observationTime.getDayOfYear(), row.getDay());
    }

    @Test
    void toDecoderPvMapsStoredActualGenerationByTradeHour() {
        PvActualHourlyDataRepository repository = mock(PvActualHourlyDataRepository.class);
        WeatherService service = new WeatherService(null, null, repository);
        LocalDate baseDate = LocalDate.parse("2026-05-11");
        when(repository.findBySourceAndRegionAndFuelTypeAndTradeDateOrderByTradeHourAsc(
                WeatherService.DEFAULT_PV_ACTUAL_SOURCE,
                "서울시",
                WeatherService.DEFAULT_PV_FUEL_TYPE,
                baseDate
        )).thenReturn(IntStream.range(0, 24)
                .mapToObj(hour -> pvActualRow(baseDate, hour, hour * 1.5))
                .toList());

        List<PvPredictionRequest.PvHourly> result = service.toDecoderPv(baseDate, "서울시");

        assertEquals(24, result.size());
        assertEquals(0, result.get(0).getHour());
        assertEquals(0.0, result.get(0).getPvPower());
        assertEquals(23, result.get(23).getHour());
        assertEquals(34.5, result.get(23).getPvPower());
    }

    @Test
    void toDecoderPvRejectsIncompleteActualGenerationWindow() {
        PvActualHourlyDataRepository repository = mock(PvActualHourlyDataRepository.class);
        WeatherService service = new WeatherService(null, null, repository);
        LocalDate baseDate = LocalDate.parse("2026-05-11");
        when(repository.findBySourceAndRegionAndFuelTypeAndTradeDateOrderByTradeHourAsc(
                WeatherService.DEFAULT_PV_ACTUAL_SOURCE,
                "제주도",
                WeatherService.DEFAULT_PV_FUEL_TYPE,
                baseDate
        )).thenReturn(List.of(pvActualRow(baseDate, 0, 1.0)));

        IllegalStateException exception = assertThrows(
                IllegalStateException.class,
                () -> service.toDecoderPv(baseDate, "제주도")
        );

        assertTrue(exception.getMessage().contains("PV 실제 발전량 데이터 부족"));
    }

    private WeatherRawData weatherRow(LocalDateTime observationTime, Double temperature) {
        return WeatherRawData.builder()
                .asosStationId(112)
                .observationTime(observationTime)
                .temperature(temperature)
                .rainfall(0.0)
                .humidity(50.0)
                .snowfall(0.0)
                .cloudCover(3.0)
                .sunshineDuration(0.5)
                .solarRadiation(1.2)
                .build();
    }

    private PvActualHourlyData pvActualRow(LocalDate tradeDate, int hour, double generationMwh) {
        return PvActualHourlyData.builder()
                .source(WeatherService.DEFAULT_PV_ACTUAL_SOURCE)
                .region("서울시")
                .fuelType(WeatherService.DEFAULT_PV_FUEL_TYPE)
                .tradeDate(tradeDate)
                .tradeHour(hour + 1)
                .observedAt(tradeDate.atStartOfDay().plusHours(hour))
                .generationMwh(generationMwh)
                .build();
    }
}
