package com.ev.multiev_charging_management_system.mqtt.service;

import com.ev.multiev_charging_management_system.mqtt.dto.ChargerMeasurementResponse;
import com.ev.multiev_charging_management_system.mqtt.entity.ChargerMeasurementHistory;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChargerMeasurementCacheService {

    public static final int LATEST_SNAPSHOT_LIMIT = 11;
    private static final String LATEST_SNAPSHOT_KEY = "charger:measurement:latest:snapshot";
    private static final Duration LATEST_TTL = Duration.ofMinutes(5);
    private static final TypeReference<List<ChargerMeasurementResponse>> SNAPSHOT_TYPE =
            new TypeReference<>() {
            };

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper = JsonMapper.builder()
            .addModule(new JavaTimeModule())
            .findAndAddModules()
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
            .visibility(PropertyAccessor.FIELD, JsonAutoDetect.Visibility.ANY)
            .build();

    public void cacheLatest(ChargerMeasurementHistory measurementHistory) {
        cacheLatestSnapshot(List.of(measurementHistory));
    }

    public List<ChargerMeasurementResponse> getLatestSnapshot() {
        try {
            String cachedSnapshot = redisTemplate.opsForValue().get(LATEST_SNAPSHOT_KEY);
            if (cachedSnapshot == null || cachedSnapshot.isBlank()) {
                return List.of();
            }

            return objectMapper.readValue(cachedSnapshot, SNAPSHOT_TYPE)
                    .stream()
                    .filter(Objects::nonNull)
                    .sorted(Comparator.comparing(ChargerMeasurementResponse::getId))
                    .toList();
        } catch (JsonProcessingException e) {
            log.warn("충전기 측정값 Redis 역직렬화 실패. DB 조회로 대체합니다.", e);
            return List.of();
        } catch (RuntimeException e) {
            log.warn("충전기 측정값 Redis 조회 실패. DB 조회로 대체합니다.", e);
            return List.of();
        }
    }

    public void cacheLatestSnapshot(List<ChargerMeasurementHistory> measurementHistories) {
        try {
            List<ChargerMeasurementResponse> incomingSnapshot = measurementHistories.stream()
                    .map(ChargerMeasurementResponse::from)
                    .toList();

            List<ChargerMeasurementResponse> latestSnapshot = Stream.concat(
                            getLatestSnapshot().stream(),
                            incomingSnapshot.stream()
                    )
                    .filter(response -> response.getId() != null)
                    .collect(Collectors.toMap(
                            ChargerMeasurementResponse::getId,
                            Function.identity(),
                            (previous, current) -> current
                    ))
                    .values()
                    .stream()
                    .sorted(Comparator.comparing(ChargerMeasurementResponse::getId).reversed())
                    .limit(LATEST_SNAPSHOT_LIMIT)
                    .sorted(Comparator.comparing(ChargerMeasurementResponse::getId))
                    .toList();

            redisTemplate.opsForValue().set(
                    LATEST_SNAPSHOT_KEY,
                    objectMapper.writeValueAsString(latestSnapshot),
                    LATEST_TTL
            );
        } catch (JsonProcessingException e) {
            log.warn("충전기 측정값 Redis 직렬화 실패. key={}", LATEST_SNAPSHOT_KEY, e);
        } catch (RuntimeException e) {
            log.warn("충전기 측정값 Redis 캐싱 실패. key={}", LATEST_SNAPSHOT_KEY, e);
        }
    }
}
