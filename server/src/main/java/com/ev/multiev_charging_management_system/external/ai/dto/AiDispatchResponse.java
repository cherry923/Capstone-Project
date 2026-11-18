package com.ev.multiev_charging_management_system.external.ai.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import tools.jackson.databind.JsonNode;

/**
 * AI dispatch-24h 응답 DTO.
 *
 * data는 dispatch commands, forecast provenance, model diagnostics를 보존하기 위해 JsonNode로 둔다.
 */
@Getter
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class AiDispatchResponse {

    @JsonProperty("request_id")
    private String requestId;

    private String code;
    private String message;

    @JsonProperty("model_version")
    private String modelVersion;

    private JsonNode data;
}
