package com.ev.multiev_charging_management_system.external.ai.controller;

import com.ev.multiev_charging_management_system.external.ai.dispatch.service.AiDispatchQueryService;
import com.ev.multiev_charging_management_system.external.ai.dispatch.service.AiDispatchService;
import com.ev.multiev_charging_management_system.external.ai.dto.AiApiResponse;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchRequest;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchResponse;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchRunQueryResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * Internal/demo AI dispatch integration endpoint.
 *
 * This is not the final IoT command API; it exposes the current Python AI full-flow result for inspection.
 */
@RestController
@RequestMapping("/api/v1/ai")
@RequiredArgsConstructor
public class AiDispatchController {

    private final AiDispatchService aiDispatchService;
    private final AiDispatchQueryService aiDispatchQueryService;

    @PostMapping("/dispatch-24h")
    public AiDispatchResponse dispatch24h(@RequestBody AiDispatchRequest request) {
        return aiDispatchService.dispatch24h(request);
    }

    @GetMapping("/dispatch-runs")
    public AiApiResponse<List<AiDispatchRunQueryResponse.Summary>> recentDispatchRuns(
            @RequestParam(defaultValue = "20") int limit
    ) {
        return AiApiResponse.success(
                null,
                "AI dispatch 실행 이력 조회가 정상적으로 완료되었습니다.",
                null,
                aiDispatchQueryService.recentRuns(limit)
        );
    }

    @GetMapping("/dispatch-runs/latest")
    public AiApiResponse<AiDispatchRunQueryResponse.Detail> latestDispatchRun() {
        return AiApiResponse.fromRun(aiDispatchQueryService.latestRun());
    }

    @GetMapping("/dispatch-runs/{runId}")
    public AiApiResponse<AiDispatchRunQueryResponse.Detail> dispatchRun(@PathVariable Long runId) {
        return AiApiResponse.fromRun(aiDispatchQueryService.getRun(runId));
    }
}
