package com.ev.multiev_charging_management_system.external.ai.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * AI 예측 모듈 PV 발전량 예측 응답 DTO.
 * 공통 응답 규격을 따른다.
 */
@Getter
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class PvPredictionResponse {

    @JsonProperty("request_id")
    private String requestId;

    private String code;
    private String message;

    @JsonProperty("model_version")
    private String modelVersion;

    private PvData data;

    @Getter
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class PvData {

        @JsonProperty("station_id")
        private Integer stationId;

        @JsonProperty("base_date")
        private String baseDate;

        @JsonProperty("target_date")
        private String targetDate;

        @JsonProperty("predicted_pv_24h")
        private List<PvHourly> predictedPv24h;
    }

    @Getter
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class PvHourly {
        private Integer hour;

        @JsonProperty("pv_power")
        private Double pvPower;
    }
}
