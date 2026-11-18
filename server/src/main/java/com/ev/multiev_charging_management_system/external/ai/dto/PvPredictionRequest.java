package com.ev.multiev_charging_management_system.external.ai.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Builder;
import lombok.Getter;

import java.util.List;

/**
 * AI 예측 모듈 PV 발전량 예측 요청 DTO.
 * POST /api/v1/ai/predictions/pv
 */
@Getter
@Builder
public class PvPredictionRequest {

    @JsonProperty("request_id")
    private String requestId;

    private String timezone;

    @JsonProperty("station_id")
    private Integer stationId;

    @JsonProperty("base_date")
    private String baseDate;

    @JsonProperty("encoder_weather_24h")
    private List<WeatherHourly> encoderWeather24h;

    @JsonProperty("encoder_weather_168h")
    private List<WeatherHourly> encoderWeather168h;

    @JsonProperty("decoder_pv_24h")
    private List<PvHourly> decoderPv24h;

    @Getter
    @Builder
    public static class WeatherHourly {
        private Integer hour;
        private Double temperature;
        private Double rain;
        private Double humidity;
        private Double snow;
        private Double cloud;
        private Double duration;
        private Double radiation;
        private Integer day;
    }

    @Getter
    @Builder
    public static class PvHourly {
        private Integer hour;

        @JsonProperty("pv_power")
        private Double pvPower;
    }
}
