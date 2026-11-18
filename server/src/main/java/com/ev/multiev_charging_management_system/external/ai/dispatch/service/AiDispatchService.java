package com.ev.multiev_charging_management_system.external.ai.dispatch.service;

import com.ev.multiev_charging_management_system.external.ai.AiModuleException;
import com.ev.multiev_charging_management_system.external.ai.AiPredictionClient;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchRequest;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchResponse;
import com.ev.multiev_charging_management_system.external.ai.dto.PvPredictionRequest;
import com.ev.multiev_charging_management_system.external.weather.entity.WeatherRawData;
import com.ev.multiev_charging_management_system.external.weather.service.KmaSolarNwpForecastService;
import com.ev.multiev_charging_management_system.external.weather.service.WeatherService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.List;

import static com.ev.multiev_charging_management_system.external.weather.service.WeatherService.DEFAULT_PV_ACTUAL_SOURCE;
import static com.ev.multiev_charging_management_system.external.weather.service.WeatherService.DEFAULT_PV_FUEL_TYPE;
import static com.ev.multiev_charging_management_system.external.weather.service.WeatherService.DEFAULT_PV_REGION;

@Service
@RequiredArgsConstructor
public class AiDispatchService {

    private static final int DEFAULT_ASOS_STATION_ID = 184;
    private static final int PV_DAY_HOURS = 24;
    private static final int PV_ENCODER_CONTEXT_HOURS = 168;

    private final AiPredictionClient aiPredictionClient;
    private final AiDispatchPersistenceService aiDispatchPersistenceService;
    private final KmaSolarNwpForecastService kmaSolarNwpForecastService;
    private final WeatherService weatherService;
    private final ObjectMapper objectMapper;

    public AiDispatchResponse dispatch24h(AiDispatchRequest request) {
        AiDispatchRequest dispatchRequest = enrichAsosActualWeatherIfRequested(request);
        dispatchRequest = enrichKmaForecastWeatherIfRequested(dispatchRequest);
        try {
            AiDispatchResponse response = aiPredictionClient.dispatch24h(dispatchRequest);
            aiDispatchPersistenceService.save(dispatchRequest, response);
            return response;
        } catch (AiModuleException exception) {
            aiDispatchPersistenceService.saveFailure(dispatchRequest, exception);
            throw exception;
        }
    }

    private AiDispatchRequest enrichAsosActualWeatherIfRequested(AiDispatchRequest request) {
        if (!Boolean.TRUE.equals(request.getUseAsosActualWeather())) {
            return request;
        }
        if (request.getTargetDate() == null || request.getTargetDate().isBlank()) {
            throw new AiModuleException("ASOS 실제 관측 입력 생성을 위해 target_date가 필요합니다.");
        }

        LocalDate targetDate = parseDate(request.getTargetDate(), "target_date");
        LocalDate baseDate = request.getBaseDate() == null || request.getBaseDate().isBlank()
                ? targetDate.minusDays(1)
                : parseDate(request.getBaseDate(), "base_date");
        int asosStationId = request.getAsosStationId() == null
                ? DEFAULT_ASOS_STATION_ID
                : request.getAsosStationId();

        List<WeatherRawData> targetWeather = weatherService.getDaily(targetDate, asosStationId);
        List<WeatherRawData> encoderWindow = weatherService.getEncoderWindow(baseDate, asosStationId);
        validateHourlyRows(targetWeather, PV_DAY_HOURS, "target_date ASOS weather", targetDate, asosStationId);
        validateHourlyRows(encoderWindow, PV_ENCODER_CONTEXT_HOURS, "encoder ASOS weather", baseDate, asosStationId);

        JsonNode targetWeather24h = toJsonNode(weatherService.toEncoderWeather(targetWeather));
        if (request.getBaseDate() == null || request.getBaseDate().isBlank()) {
            request.setBaseDate(baseDate.toString());
        }
        if (request.getEncoderWeather24h() == null) {
            request.setEncoderWeather24h(targetWeather24h);
        }
        if (request.getEncoderWeather168h() == null) {
            request.setEncoderWeather168h(toJsonNode(weatherService.toEncoderWeather168h(encoderWindow)));
        }
        if (request.getDecoderWeather24h() == null) {
            request.setDecoderWeather24h(targetWeather24h);
        }
        if (request.getFutureWeather24h() == null) {
            request.setFutureWeather24h(targetWeather24h);
        }
        if (request.getDecoderPv24h() == null) {
            request.setDecoderPv24h(toDecoderPvJson(request, baseDate));
        }
        return request;
    }

    private void validateHourlyRows(List<WeatherRawData> rows, int expectedCount, String label,
                                    LocalDate referenceDate, int asosStationId) {
        if (rows.size() < expectedCount) {
            throw new AiModuleException("%s 부족: date=%s, asosStationId=%d, expected=%d, actual=%d"
                    .formatted(label, referenceDate, asosStationId, expectedCount, rows.size()));
        }
    }

    private AiDispatchRequest enrichKmaForecastWeatherIfRequested(AiDispatchRequest request) {
        if (!Boolean.TRUE.equals(request.getUseKmaForecastWeather())) {
            return request;
        }
        if (request.getTargetDate() == null || request.getTargetDate().isBlank()) {
            throw new AiModuleException("KMA 수치예보 입력 생성을 위해 target_date가 필요합니다.");
        }

        LocalDate targetDate = parseDate(request.getTargetDate(), "target_date");
        if (request.getBaseDate() == null || request.getBaseDate().isBlank()) {
            request.setBaseDate(targetDate.minusDays(1).toString());
        }

        if (request.getEncoderWeather24h() == null) {
            List<PvPredictionRequest.WeatherHourly> weather24h = buildWeather24h(request, targetDate);
            request.setEncoderWeather24h(toJsonNode(weather24h));
        }
        if (request.getDecoderPv24h() == null) {
            request.setDecoderPv24h(toDecoderPvJson(request, parseDate(request.getBaseDate(), "base_date")));
        }
        return request;
    }

    private List<PvPredictionRequest.WeatherHourly> buildWeather24h(AiDispatchRequest request, LocalDate targetDate) {
        if (request.getNwpIssuedAtUtc() == null || request.getNwpIssuedAtUtc().isBlank()) {
            return kmaSolarNwpForecastService.buildPvEncoderWeather24h(
                    targetDate,
                    request.getForecastLatitude(),
                    request.getForecastLongitude()
            );
        }
        return kmaSolarNwpForecastService.buildPvEncoderWeather24h(
                targetDate,
                request.getForecastLatitude(),
                request.getForecastLongitude(),
                parseDateTime(request.getNwpIssuedAtUtc(), "nwp_issued_at_utc")
        );
    }

    private JsonNode toJsonNode(Object value) {
        try {
            return objectMapper.readTree(objectMapper.writeValueAsString(value));
        } catch (Exception exception) {
            throw new AiModuleException("AI dispatch 요청 JSON 변환에 실패했습니다.", exception);
        }
    }

    private JsonNode toDecoderPvJson(AiDispatchRequest request, LocalDate baseDate) {
        try {
            return toJsonNode(weatherService.toDecoderPv(
                    baseDate,
                    defaultIfBlank(request.getPvRegion(), DEFAULT_PV_REGION),
                    defaultIfBlank(request.getPvActualSource(), DEFAULT_PV_ACTUAL_SOURCE),
                    defaultIfBlank(request.getPvFuelType(), DEFAULT_PV_FUEL_TYPE)
            ));
        } catch (IllegalStateException exception) {
            throw new AiModuleException(exception.getMessage(), exception);
        }
    }

    private String defaultIfBlank(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }

    private LocalDate parseDate(String value, String fieldName) {
        try {
            return LocalDate.parse(value);
        } catch (DateTimeParseException exception) {
            throw new AiModuleException(fieldName + " must be YYYY-MM-DD.", exception);
        }
    }

    private LocalDateTime parseDateTime(String value, String fieldName) {
        try {
            return LocalDateTime.parse(value);
        } catch (DateTimeParseException exception) {
            throw new AiModuleException(fieldName + " must be ISO local datetime, for example 2026-05-11T00:00:00.", exception);
        }
    }
}
