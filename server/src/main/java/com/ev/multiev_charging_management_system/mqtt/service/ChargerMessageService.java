package com.ev.multiev_charging_management_system.mqtt.service;

import com.ev.multiev_charging_management_system.external.mqtt.dto.ChargerMeasurementDto;
import com.ev.multiev_charging_management_system.mqtt.entity.ChargerMeasurementHistory;
import com.ev.multiev_charging_management_system.mqtt.repository.ChargerMeasurementRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

/**
 * MQTT로 수신한 충전기 상태 정보를 저장하는 서비스 객체
 *
 * <p>충전기 상태 정보를 버퍼에 추가하고, 가상 충전소 상태 데이터를 함께 생성합니다.
 * 버퍼에 일정 개수 이상의 데이터가 쌓이면 배치 단위로 저장소에 저장합니다.
 */
@Service
@RequiredArgsConstructor
public class ChargerMessageService {

    private static final int batchSize = 5;

    private final ChargerMeasurementRepository chargerMessageRepository;
    private final VirtualStationEssStateService virtualStationEssStateService;
    private final ChargerMeasurementCacheService chargerMeasurementCacheService;

    private final List<ChargerMeasurementHistory> buffer = new ArrayList<>();
    private final Map<String, Boolean> virtualChargingStates = new HashMap<>();

    /**
     * 충전기 상태 정보를 검증한 뒤 저장 버퍼에 추가합니다.
     *
     * <p>수신한 실제 상태 정보와 함께 가상 충전소 상태 정보를 생성하여 버퍼에 추가합니다.
     * 버퍼 크기가 배치 기준에 도달하면 전체 데이터를 저장하고 버퍼를 초기화합니다.
     *
     * @param measurementDto MQTT에서 수신한 충전기 상태 데이터
     * @param topic 메시지가 수신된 MQTT 토픽
     */
    @Transactional
    public void saveMessage(ChargerMeasurementDto measurementDto, String topic) {
        validate(measurementDto);

        buffer.add(ChargerMeasurementHistory.from(measurementDto, topic));

        if (buffer.size() >= batchSize) {

            List<ChargerMeasurementHistory> virtualMeasurements =
                    createVirtualMeasurements();

            buffer.addAll(virtualMeasurements);

            List<ChargerMeasurementHistory> batch = new ArrayList<>(buffer);
            buffer.clear();
            List<ChargerMeasurementHistory> savedBatch =
                    chargerMessageRepository.saveAll(batch);
            chargerMeasurementCacheService.cacheLatestSnapshot(savedBatch);
        }
    }

    /**
     * 가상 충전소의 충전기 상태 정보를 생성합니다.
     *
     * <p>ST002, ST003 충전소의 1번부터 3번 충전기에 대한 가상 데이터를 생성합니다.
     *
     * @return 저장 버퍼에 추가할 가상 충전기 상태 정보 목록
     */
    private List<ChargerMeasurementHistory> createVirtualMeasurements() {
        return List.of(
                createVirtualMeasurement("ST002", 1),
                createVirtualMeasurement("ST002", 2),
                createVirtualMeasurement("ST002", 3),
                createVirtualMeasurement("ST003", 1),
                createVirtualMeasurement("ST003", 2),
                createVirtualMeasurement("ST003", 3)
        );
    }

    /**
     * 지정한 가상 충전소와 충전기 번호에 대한 충전기 측정 이력을 생성합니다.
     *
     * <p>충전 여부, 출력, 전압, 전류 값은 {@link #generateVirtualChargerSample(String, Integer)}
     * 메서드에서 생성한 샘플 값을 사용합니다. ESS 잔량은 충전소 단위 상태를 관리하는
     * {@link VirtualStationEssStateService}에서 조회한 값을 사용합니다.
     *
     * @param stationId 가상 충전소 ID
     * @param chargerNo 가상 충전기 번호
     * @return 생성된 가상 충전기 측정 이력
     */
    private ChargerMeasurementHistory createVirtualMeasurement(
            String stationId,
            Integer chargerNo
    ) {
        VirtualChargerSample sample =
                generateVirtualChargerSample(stationId, chargerNo);

        return ChargerMeasurementHistory.virtual(
                stationId,
                chargerNo,
                sample.charging(),
                sample.power(),
                sample.voltage(),
                sample.current(),
                virtualStationEssStateService.getEssRemain(stationId),
                "iot.data/" + stationId + chargerNo + "telemetry"
        );
    }

    /**
     * 지정한 가상 충전기의 충전 상태와 전기 측정값 샘플을 생성합니다.
     *
     * <p>충전기별 이전 충전 상태를 {@code virtualChargingStates}에 저장해두고,
     * 낮은 확률로만 충전/대기 상태를 전환합니다. 이를 통해 MQTT 메시지가 짧은 간격으로
     * 수신되더라도 가상 충전기가 너무 자주 활성화/비활성화되지 않도록 합니다.
     *
     * <p>충전 중인 경우 급속 충전기에 적합한 범위의 출력과 전압을 생성하고,
     * 전류는 {@code power * 1000 / voltage} 공식을 사용해 계산합니다. 대기 중인 경우
     * 출력, 전압, 전류는 모두 0으로 반환합니다.
     *
     * @param stationId 가상 충전소 ID
     * @param chargerNo 가상 충전기 번호
     * @return 가상 충전기의 충전 상태, 출력, 전압, 전류 샘플
     */
    private VirtualChargerSample generateVirtualChargerSample(
            String stationId,
            Integer chargerNo
    ) {
        String key = stationId + ":" + chargerNo;

        boolean charging = virtualChargingStates.computeIfAbsent(
                key,
                ignored -> ThreadLocalRandom.current().nextDouble() < 0.65
        );

        double changeProbability = charging ? 0.08 : 0.12;
        if (ThreadLocalRandom.current().nextDouble() < changeProbability) {
            charging = !charging;
            virtualChargingStates.put(key, charging);
        }

        if (!charging) {
            return new VirtualChargerSample(false, 0, 0.0, 0.0);
        }

        int power = generatePower();
        double voltage = generateVoltage();
        double current = Math.round((power * 1000.0 / voltage) * 10.0) / 10.0;

        return new VirtualChargerSample(true, power, voltage, current);
    }

    private record VirtualChargerSample(
            boolean charging,
            Integer power,
            Double voltage,
            Double current
    ) {
    }

    /**
     * 가상 충전기 전력 값을 생성합니다.
     *
     * @return 가상 충전기 전력 값
     */
    private Integer generatePower() {
        return ThreadLocalRandom.current().nextInt(50, 121);
    }

    /**
     * 가상 충전기 전압 값을 생성합니다.
     *
     * @return 가상 충전기 전압 값
     */
    private Double generateVoltage() {
        return Math.round(
                ThreadLocalRandom.current().nextDouble(720.0, 780.0) * 10.0
        ) / 10.0;
    }

    /**
     * 충전기 상태 정보의 필수 값을 검증합니다.
     *
     * @param measurementDto 검증할 충전기 상태 정보
     * @throws IllegalArgumentException 충전소 ID 또는 충전기 번호가 누락된 경우
     */
    private void validate(ChargerMeasurementDto measurementDto) {
        if (measurementDto.getStationId() == null || measurementDto.getStationId().isBlank()) {
            throw new IllegalArgumentException("stationId는 필수입니다.");
        }

        if (measurementDto.getChargerNo() == null ) {
            throw new IllegalArgumentException("chargerNo는 필수입니다.");
        }
    }
}
