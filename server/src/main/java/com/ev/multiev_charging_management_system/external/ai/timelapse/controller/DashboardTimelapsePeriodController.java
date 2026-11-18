package com.ev.multiev_charging_management_system.external.ai.timelapse.controller;

import com.ev.multiev_charging_management_system.external.ai.dto.AiApiResponse;
import com.ev.multiev_charging_management_system.external.ai.timelapse.dto.DashboardTimelapseMqttPublishResponse;
import com.ev.multiev_charging_management_system.external.ai.timelapse.dto.DashboardTimelapseResponse;
import com.ev.multiev_charging_management_system.external.ai.timelapse.dto.DashboardTimelapseUpsertRequest;
import com.ev.multiev_charging_management_system.external.ai.timelapse.service.DashboardTimelapseMqttPublishService;
import com.ev.multiev_charging_management_system.external.ai.timelapse.service.DashboardTimelapsePeriodService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/ai/timelapse-periods")
public class DashboardTimelapsePeriodController {

    private final DashboardTimelapsePeriodService timelapsePeriodService;
    private final DashboardTimelapseMqttPublishService timelapseMqttPublishService;

    @GetMapping
    public AiApiResponse<List<DashboardTimelapseResponse.Summary>> activePeriods() {
        return AiApiResponse.success(
                null,
                "대시보드 타임랩스 기간 목록 조회가 완료되었습니다.",
                null,
                timelapsePeriodService.activePeriods()
        );
    }

    @GetMapping("/latest")
    public AiApiResponse<DashboardTimelapseResponse.Detail> latestPeriod() {
        return AiApiResponse.success(
                null,
                "대시보드 타임랩스 최신 기간 조회가 완료되었습니다.",
                null,
                timelapsePeriodService.latestActivePeriod()
        );
    }

    @GetMapping("/{periodKey}")
    public AiApiResponse<DashboardTimelapseResponse.Detail> period(@PathVariable String periodKey) {
        return AiApiResponse.success(
                null,
                "대시보드 타임랩스 기간 조회가 완료되었습니다.",
                null,
                timelapsePeriodService.getPeriod(periodKey)
        );
    }

    @PostMapping
    public ResponseEntity<AiApiResponse<DashboardTimelapseResponse.Detail>> upsertPeriod(
            @RequestBody DashboardTimelapseUpsertRequest request
    ) {
        DashboardTimelapseResponse.Detail detail = timelapsePeriodService.upsertPeriod(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(AiApiResponse.success(
                null,
                "대시보드 타임랩스 기간 저장이 완료되었습니다.",
                null,
                detail
        ));
    }

    @PostMapping("/{periodKey}/frames/{frameIndex}/mqtt-publish")
    public AiApiResponse<DashboardTimelapseMqttPublishResponse> publishFrameToMqtt(
            @PathVariable String periodKey,
            @PathVariable int frameIndex,
            @RequestParam(defaultValue = "demo") String mode,
            @RequestParam(defaultValue = "dashboard") String trigger
    ) {
        return AiApiResponse.success(
                null,
                "대시보드 타임랩스 프레임 MQTT 발행이 완료되었습니다.",
                null,
                timelapseMqttPublishService.publishFrame(periodKey, frameIndex, mode, trigger)
        );
    }
}
