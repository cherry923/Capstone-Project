package com.ev.multiev_charging_management_system.external.ai.dto;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import tools.jackson.databind.JsonNode;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * AI dispatch-24h 요청 DTO.
 *
 * 현재 단계에서는 백엔드가 충전소 상태를 DB에서 조립하지 않고, 데모/통합 요청 body를 AI 서버로 전달한다.
 * Python dispatch flow의 optional 필드가 자주 바뀔 수 있어 알 수 없는 필드는 extraFields로 보존한다.
 */
@Getter
@Setter
@NoArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AiDispatchRequest {

    @JsonProperty("request_id")
    private String requestId;

    private String timezone;

    @JsonProperty("target_date")
    private String targetDate;

    @JsonProperty("base_date")
    private String baseDate;

    @JsonProperty("station_id")
    private Object stationId;

    @JsonProperty("use_team_model")
    private Boolean useTeamModel;

    @JsonProperty("init_soc")
    private List<Double> initSoc;

    @JsonProperty("ev_scale")
    private Double evScale;

    /**
     * "single_charger" or "regional_virtual_hub". When null, the AI module auto-selects:
     * an aggregate (jeju_total) EV payload defaults to regional_virtual_hub (scaled-up hub
     * physics, ev_scale=1.0), while explicit station-level demand defaults to single_charger.
     */
    @JsonProperty("scenario_mode")
    private String scenarioMode;

    private JsonNode stations;

    @JsonProperty("tou_24h")
    private JsonNode tou24h;

    @JsonProperty("encoder_weather_24h")
    private JsonNode encoderWeather24h;

    @JsonProperty("encoder_weather_168h")
    private JsonNode encoderWeather168h;

    @JsonProperty("decoder_weather_24h")
    private JsonNode decoderWeather24h;

    @JsonProperty("future_weather_24h")
    private JsonNode futureWeather24h;

    @JsonProperty("decoder_pv_24h")
    private JsonNode decoderPv24h;

    @JsonProperty("aggregate_ev_demand_24h")
    private JsonNode aggregateEvDemand24h;

    @JsonProperty("station_demand_weights")
    private JsonNode stationDemandWeights;

    @JsonProperty("station_pv_scales")
    private JsonNode stationPvScales;

    @JsonProperty("use_kma_forecast_weather")
    private Boolean useKmaForecastWeather;

    @JsonProperty("use_asos_actual_weather")
    private Boolean useAsosActualWeather;

    @JsonProperty("asos_station_id")
    private Integer asosStationId;

    @JsonProperty("forecast_latitude")
    private Double forecastLatitude;

    @JsonProperty("forecast_longitude")
    private Double forecastLongitude;

    @JsonProperty("nwp_issued_at_utc")
    private String nwpIssuedAtUtc;

    @JsonProperty("pv_region")
    private String pvRegion;

    @JsonProperty("pv_actual_source")
    private String pvActualSource;

    @JsonProperty("pv_fuel_type")
    private String pvFuelType;

    @JsonIgnore
    private final Map<String, JsonNode> extraFields = new LinkedHashMap<>();

    @JsonAnySetter
    public void putExtraField(String name, JsonNode value) {
        extraFields.put(name, value);
    }

    @JsonAnyGetter
    public Map<String, JsonNode> getExtraFields() {
        return extraFields;
    }
}
