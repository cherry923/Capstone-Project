package com.ev.multiev_charging_management_system.external.ai.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

public final class AiDispatchRunQueryResponse {

    private AiDispatchRunQueryResponse() {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Summary(
            @JsonProperty("run_id")
            Long runId,
            @JsonProperty("request_id")
            String requestId,
            @JsonProperty("target_date")
            LocalDate targetDate,
            String status,
            String message,
            @JsonProperty("model_version")
            String modelVersion,
            @JsonProperty("model_name")
            String modelName,
            @JsonProperty("model_status")
            String modelStatus,
            @JsonProperty("pv_source")
            String pvSource,
            @JsonProperty("ev_source")
            String evSource,
            @JsonProperty("team_model_source")
            String teamModelSource,
            @JsonProperty("command_count")
            Integer commandCount,
            @JsonProperty("created_at")
            LocalDateTime createdAt
    ) {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Detail(
            Summary run,
            List<Command> commands,
            @JsonProperty("request_payload")
            Object requestPayload,
            @JsonProperty("response_payload")
            Object responsePayload
    ) {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Command(
            @JsonProperty("command_index")
            Integer commandIndex,
            Integer hour,
            @JsonProperty("station_id")
            String stationId,
            @JsonProperty("share_energy_kwh")
            Double shareEnergyKwh,
            @JsonProperty("ess_action")
            Double essAction,
            @JsonProperty("raw_ess_action")
            Double rawEssAction,
            @JsonProperty("pv_priority")
            Double pvPriority,
            @JsonProperty("soc_before")
            Double socBefore,
            @JsonProperty("soc_after")
            Double socAfter,
            @JsonProperty("grid_total_kwh")
            Double gridTotalKwh,
            @JsonProperty("grid_cost")
            Double gridCost,
            String command,
            @JsonProperty("safety_adjusted")
            Boolean safetyAdjusted,
            @JsonProperty("command_payload")
            Object commandPayload
    ) {
    }
}
