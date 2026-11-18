package com.ev.multiev_charging_management_system.external.weather.service;

import com.ev.multiev_charging_management_system.external.ai.dto.PvPredictionRequest;
import com.ev.multiev_charging_management_system.external.weather.KmaSolarNwpApiClient;
import com.ev.multiev_charging_management_system.external.weather.dto.KmaSolarNwpForecastValue;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.IntStream;

import static org.junit.jupiter.api.Assertions.assertEquals;

class KmaSolarNwpForecastServiceTest {

    @Test
    void buildPvEncoderWeather24hConvertsKmaForecastToPvWeatherRows() {
        KmaSolarNwpApiClient client = new StubKmaSolarNwpApiClient();
        KmaSolarNwpForecastService service = new KmaSolarNwpForecastService(client, 33.5, 126.5);

        List<PvPredictionRequest.WeatherHourly> result = service.buildPvEncoderWeather24h(
                LocalDate.of(2026, 5, 12),
                33.499621,
                126.531188,
                LocalDateTime.of(2026, 5, 11, 0, 0)
        );

        assertEquals(24, result.size());
        assertEquals(0, result.get(0).getHour());
        assertEquals(132, result.get(0).getDay());
        assertEquals(16.0, result.get(0).getTemperature());
        assertEquals(80.0, result.get(0).getHumidity());
        assertEquals(10.0, result.get(0).getCloud());
        assertEquals(0.36, result.get(0).getRadiation(), 1e-9);
        assertEquals(0.36, result.get(0).getDuration(), 1e-9);

        assertEquals(17.0, result.get(1).getTemperature());
        assertEquals(0.48, result.get(1).getRadiation(), 1e-9);
    }

    private static class StubKmaSolarNwpApiClient extends KmaSolarNwpApiClient {

        StubKmaSolarNwpApiClient() {
            super("http://localhost", "test-key", "KIMG");
        }

        @Override
        public List<KmaSolarNwpForecastValue> getForecast(
                String variable,
                LocalDateTime issuedAtUtc,
                LocalDateTime startUtc,
                LocalDateTime endUtc,
                int intervalHours,
                double latitude,
                double longitude
        ) {
            return IntStream.rangeClosed(0, 8)
                    .mapToObj(index -> new KmaSolarNwpForecastValue(
                            issuedAtUtc,
                            startUtc.plusHours(index * 3L),
                            variable,
                            longitude,
                            latitude,
                            valueFor(variable, index)
                    ))
                    .toList();
        }

        private double valueFor(String variable, int index) {
            return switch (variable) {
                case "DSWRF" -> 100.0 + (100.0 * index);
                case "TMP" -> 16.0 + (3.0 * index);
                case "RH" -> 80.0 - index;
                case "TCDC" -> 1.0;
                case "SNOD" -> 0.0;
                default -> 0.0;
            };
        }
    }
}
