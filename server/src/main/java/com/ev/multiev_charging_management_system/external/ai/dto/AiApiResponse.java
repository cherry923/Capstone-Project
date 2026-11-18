package com.ev.multiev_charging_management_system.external.ai.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiApiResponse<T>(
        @JsonProperty("request_id")
        String requestId,
        String code,
        String message,
        @JsonProperty("model_version")
        String modelVersion,
        T data
) {

    public static <T> AiApiResponse<T> success(String requestId, String message, String modelVersion, T data) {
        return new AiApiResponse<>(requestId, "SUCCESS", message, modelVersion, data);
    }

    public static AiApiResponse<AiDispatchRunQueryResponse.Detail> fromRun(AiDispatchRunQueryResponse.Detail detail) {
        AiDispatchRunQueryResponse.Summary run = detail.run();
        return new AiApiResponse<>(
                run.requestId(),
                run.status(),
                run.message(),
                run.modelVersion(),
                detail
        );
    }
}
