package com.ev.multiev_charging_management_system.external.ai.timelapse.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public record DashboardTimelapseMqttPublishResponse(
        @JsonProperty("period_key")
        String periodKey,
        @JsonProperty("frame_index")
        int frameIndex,
        @JsonProperty("frame_date")
        LocalDate frameDate,
        int hour,
        String mode,
        @JsonProperty("topic_namespace")
        String topicNamespace,
        @JsonProperty("published_at")
        LocalDateTime publishedAt,
        List<PublishedCommand> commands
) {

    public record PublishedCommand(
            @JsonProperty("station_id")
            String stationId,
            String topic,
            Map<String, Object> payload
    ) {
    }
}
