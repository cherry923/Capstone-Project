package com.ev.multiev_charging_management_system.external.ai.timelapse.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

public final class DashboardTimelapseResponse {

    private DashboardTimelapseResponse() {
    }

    public record Summary(
            @JsonProperty("period_key")
            String periodKey,
            String label,
            @JsonProperty("start_date")
            LocalDate startDate,
            @JsonProperty("end_date")
            LocalDate endDate,
            String description,
            String source,
            @JsonProperty("created_at")
            LocalDateTime createdAt,
            @JsonProperty("updated_at")
            LocalDateTime updatedAt
    ) {
    }

    public record Detail(
            @JsonProperty("period_key")
            String periodKey,
            String label,
            @JsonProperty("start_date")
            LocalDate startDate,
            @JsonProperty("end_date")
            LocalDate endDate,
            String description,
            String source,
            List<Frame> frames
    ) {
    }

    public record Frame(
            @JsonProperty("frame_index")
            int frameIndex,
            @JsonProperty("frame_date")
            LocalDate frameDate,
            int hour,
            List<StationFrame> stations
    ) {
    }

    public record StationFrame(
            @JsonProperty("station_id")
            String stationId,
            @JsonProperty("station_name")
            String stationName,
            String region,
            @JsonProperty("demand_kwh")
            double demandKwh,
            @JsonProperty("pv_kw")
            double pvKw,
            @JsonProperty("ess_percent")
            double essPercent,
            @JsonProperty("tariff_krw_per_kwh")
            double tariffKrwPerKwh,
            @JsonProperty("share_energy_kwh")
            double shareEnergyKwh,
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
