package com.ev.multiev_charging_management_system.external.ai.timelapse.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDate;
import java.util.List;

public record DashboardTimelapseUpsertRequest(
        @JsonProperty("period_key")
        String periodKey,
        String label,
        @JsonProperty("start_date")
        LocalDate startDate,
        @JsonProperty("end_date")
        LocalDate endDate,
        String description,
        String source,
        Boolean active,
        List<Frame> frames
) {

    public record Frame(
            @JsonProperty("frame_index")
            Integer frameIndex,
            @JsonProperty("frame_date")
            LocalDate frameDate,
            int hour,
            List<StationFrame> stations
    ) {
        public Frame(int hour, List<StationFrame> stations) {
            this(null, null, hour, stations);
        }
    }

    public record StationFrame(
            @JsonProperty("station_id")
            String stationId,
            @JsonProperty("station_name")
            String stationName,
            String region,
            @JsonProperty("demand_kwh")
            Double demandKwh,
            @JsonProperty("pv_kw")
            Double pvKw,
            @JsonProperty("ess_percent")
            Double essPercent,
            @JsonProperty("tariff_krw_per_kwh")
            Double tariffKrwPerKwh,
            @JsonProperty("share_energy_kwh")
            Double shareEnergyKwh,
            @JsonProperty("active_chargers")
            Integer activeChargers,
            @JsonProperty("total_chargers")
            Integer totalChargers,
            @JsonProperty("vehicle_count")
            Integer vehicleCount,
            String status,
            @JsonProperty("command_text")
            String commandText,
            @JsonProperty("policy_text")
            String policyText,
            @JsonProperty("prediction_text")
            String predictionText
    ) {
    }
}
