package com.ev.multiev_charging_management_system.mqtt.service;

import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 가상 충전소의 ESS 잔여 SOC 상태를 관리하는 서비스객체
 *
 * <p>가상 충전소별 ESS 잔여량을 메모리에 보관하며,
 * AI 디스패치 명령 발행 이후 변경된 SOC 값을 반영합니다.
 */
@Service
public class VirtualStationEssStateService {

    private final Map<String, Double> essByStation = new ConcurrentHashMap<>();

    /**
     * 가상 충전소의 초기 ESS 잔여 SOC 값을 설정합니다.
     */
    public VirtualStationEssStateService() {
        essByStation.put("ST002", 0.65);
        essByStation.put("ST003", 0.78);
    }

    /**
     * 충전소 ID에 해당하는 ESS 잔여 SOC 값을 조회합니다.
     *
     * <p>등록되지 않은 충전소 ID가 전달되면 기본값 {@code 0.5}를 반환합니다.
     *
     * @param stationId ESS 잔여량을 조회할 충전소 ID
     * @return 충전소의 ESS 잔여 SOC 값
     */
    public double getEssRemain(String stationId) {
        return essByStation.getOrDefault(stationId, 0.5);
    }

    /**
     * 충전소 ID에 해당하는 ESS 잔여 SOC 값을 갱신합니다.
     *
     * <p>{@code socAfter}가 {@code null}이면 상태를 변경하지 않습니다.
     * 값이 전달된 경우 ESS SOC 범위를 벗어나지 않도록 {@code 0.0} 이상 {@code 1.0} 이하로 보정한 뒤 저장합니다.
     *
     * @param stationId ESS 잔여량을 갱신할 충전소 ID
     * @param socAfter AI 디스패치 명령 적용 이후의 ESS 잔여 SOC 값
     */
    public void updateEssRemain(String stationId, Double socAfter) {
        if (socAfter == null) {
            return;
        }

        double clamped = Math.max(0.0, Math.min(1.0, socAfter));
        essByStation.put(stationId, clamped);
    }
}
