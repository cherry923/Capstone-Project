package com.ev.multiev_charging_management_system.mqtt.controller;

import com.ev.multiev_charging_management_system.mqtt.dto.ChargerMeasurementResponse;
import com.ev.multiev_charging_management_system.mqtt.service.ChargerMeasurementResponseService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequiredArgsConstructor
@RequestMapping({"/api/chargers/measurements", "/api/v1/chargers/measurements"})
public class ChargerMeasurementController {

    private final ChargerMeasurementResponseService queryService;

    /**
     * 최근 저장된 11개 데이터 조회
     * 데이터 발행 5개, 가상의 충전소 기록 6개로 총 11개
     */
    @GetMapping("/latest-snapshot")
    public List<ChargerMeasurementResponse> getLatestSnapshot() {
        return queryService.getLatestSnapshot();
    }

    /**
     * 마지막으로 받은 id 이후의 신규 데이터만 조회
     */
    @GetMapping("/changes")
    public List<ChargerMeasurementResponse> getChanges(
            @RequestParam Long afterId
    ) {
        return queryService.getChangesAfterId(afterId);
    }

    /**
     * 특정 충전기 데이터만 조회
     */
    @GetMapping("/{stationId}/{chargerNo}/changes")
    public List<ChargerMeasurementResponse> getChargerChanges(
            @PathVariable String stationId,
            @PathVariable Integer chargerNo,
            @RequestParam Long afterId
    ) {
        return queryService.getChangesAfterId(
                stationId,
                chargerNo,
                afterId
        );
    }
}
