package com.ev.multiev_charging_management_system.external.weather.service;

import com.ev.multiev_charging_management_system.external.ai.dto.PvPredictionRequest;
import com.ev.multiev_charging_management_system.external.weather.KmaSolarNwpApiClient;
import com.ev.multiev_charging_management_system.external.weather.KmaSolarNwpApiException;
import com.ev.multiev_charging_management_system.external.weather.dto.KmaSolarNwpForecastValue;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.*;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.NavigableMap;
import java.util.TreeMap;
import java.util.stream.IntStream;

@Service
public class KmaSolarNwpForecastService {

    private static final ZoneId KST = ZoneId.of("Asia/Seoul");
    private static final ZoneId UTC = ZoneOffset.UTC;
    private static final int FORECAST_INTERVAL_HOURS = 3;
    private static final List<String> PV_WEATHER_VARIABLES = List.of("DSWRF", "TMP", "RH", "TCDC", "SNOD");

    private final KmaSolarNwpApiClient kmaSolarNwpApiClient;
    private final double defaultLatitude;
    private final double defaultLongitude;

    public KmaSolarNwpForecastService(
            KmaSolarNwpApiClient kmaSolarNwpApiClient,
            @Value("${external.weather.kma-solar-nwp.default-latitude:33.499621}") double defaultLatitude,
            @Value("${external.weather.kma-solar-nwp.default-longitude:126.531188}") double defaultLongitude
    ) {
        this.kmaSolarNwpApiClient = kmaSolarNwpApiClient;
        this.defaultLatitude = defaultLatitude;
        this.defaultLongitude = defaultLongitude;
    }

    public List<PvPredictionRequest.WeatherHourly> buildPvEncoderWeather24h(LocalDate targetDateKst) {
        return buildPvEncoderWeather24h(targetDateKst, defaultLatitude, defaultLongitude);
    }

    public List<PvPredictionRequest.WeatherHourly> buildPvEncoderWeather24h(
            LocalDate targetDateKst,
            Double latitude,
            Double longitude
    ) {
        RuntimeException lastFailure = null;
        for (LocalDateTime issuedAtUtc : issueCandidatesUtc(LocalDateTime.now(Clock.systemUTC()))) {
            try {
                return buildPvEncoderWeather24h(targetDateKst, latitude, longitude, issuedAtUtc);
            } catch (KmaSolarNwpApiException exception) {
                lastFailure = exception;
            }
        }
        throw new KmaSolarNwpApiException("KMA solar NWP forecast lookup failed for recent issue times.", lastFailure);
    }

    public List<PvPredictionRequest.WeatherHourly> buildPvEncoderWeather24h(
            LocalDate targetDateKst,
            Double latitude,
            Double longitude,
            LocalDateTime issuedAtUtc
    ) {
        double requestLat = latitude != null ? latitude : defaultLatitude;
        double requestLon = longitude != null ? longitude : defaultLongitude;
        LocalDateTime startUtc = targetDateKst.atStartOfDay(KST).withZoneSameInstant(UTC).toLocalDateTime();
        LocalDateTime endUtc = targetDateKst.atTime(23, 0).atZone(KST).withZoneSameInstant(UTC).toLocalDateTime();

        Map<String, NavigableMap<LocalDateTime, Double>> byVariable = new LinkedHashMap<>();
        for (String variable : PV_WEATHER_VARIABLES) {
            List<KmaSolarNwpForecastValue> values = kmaSolarNwpApiClient.getForecast(
                    variable,
                    issuedAtUtc,
                    startUtc,
                    endUtc,
                    FORECAST_INTERVAL_HOURS,
                    requestLat,
                    requestLon
            );
            byVariable.put(variable, toTimeMap(values));
        }

        return IntStream.range(0, 24)
                .mapToObj(hour -> toWeatherHourly(targetDateKst, hour, byVariable))
                .toList();
    }

    public List<PvPredictionRequest.PvHourly> zeroDecoderPv24h() {
        return IntStream.range(0, 24)
                .mapToObj(hour -> PvPredictionRequest.PvHourly.builder()
                        .hour(hour)
                        .pvPower(0.0)
                        .build())
                .toList();
    }

    private PvPredictionRequest.WeatherHourly toWeatherHourly(
            LocalDate targetDateKst,
            int hour,
            Map<String, NavigableMap<LocalDateTime, Double>> byVariable
    ) {
        LocalDateTime targetUtc = targetDateKst.atTime(hour, 0).atZone(KST).withZoneSameInstant(UTC).toLocalDateTime();
        double radiationMj = Math.max(0.0, interpolate(byVariable.get("DSWRF"), targetUtc) * 0.0036);

        return PvPredictionRequest.WeatherHourly.builder()
                .hour(hour)
                .temperature(interpolate(byVariable.get("TMP"), targetUtc))
                .rain(0.0)
                .humidity(interpolate(byVariable.get("RH"), targetUtc))
                .snow(Math.max(0.0, interpolate(byVariable.get("SNOD"), targetUtc)))
                .cloud(normalizeCloud(interpolate(byVariable.get("TCDC"), targetUtc)))
                .duration(Math.min(1.0, radiationMj))
                .radiation(radiationMj)
                .day(targetDateKst.getDayOfYear())
                .build();
    }

    private NavigableMap<LocalDateTime, Double> toTimeMap(List<KmaSolarNwpForecastValue> values) {
        NavigableMap<LocalDateTime, Double> map = new TreeMap<>();
        values.stream()
                .sorted(Comparator.comparing(KmaSolarNwpForecastValue::forecastTimeUtc))
                .forEach(value -> map.put(value.forecastTimeUtc(), value.value()));
        return map;
    }

    private double interpolate(NavigableMap<LocalDateTime, Double> values, LocalDateTime targetUtc) {
        if (values == null || values.isEmpty()) {
            return 0.0;
        }
        if (values.containsKey(targetUtc)) {
            return values.get(targetUtc);
        }

        Map.Entry<LocalDateTime, Double> floor = values.floorEntry(targetUtc);
        Map.Entry<LocalDateTime, Double> ceiling = values.ceilingEntry(targetUtc);
        if (floor == null) {
            return ceiling.getValue();
        }
        if (ceiling == null) {
            return floor.getValue();
        }

        long totalSeconds = Duration.between(floor.getKey(), ceiling.getKey()).getSeconds();
        if (totalSeconds <= 0) {
            return floor.getValue();
        }
        double ratio = (double) Duration.between(floor.getKey(), targetUtc).getSeconds() / totalSeconds;
        return floor.getValue() + ((ceiling.getValue() - floor.getValue()) * ratio);
    }

    private double normalizeCloud(double value) {
        if (value <= 1.0) {
            return Math.max(0.0, value * 10.0);
        }
        if (value <= 10.0) {
            return Math.max(0.0, value);
        }
        return Math.max(0.0, value / 10.0);
    }

    private List<LocalDateTime> issueCandidatesUtc(LocalDateTime nowUtc) {
        LocalDate today = nowUtc.toLocalDate();
        LocalDateTime latest = nowUtc.getHour() >= 12 ? today.atTime(12, 0) : today.atStartOfDay();
        return List.of(
                latest,
                latest.minusHours(12),
                latest.minusHours(24),
                latest.minusHours(36)
        );
    }
}
