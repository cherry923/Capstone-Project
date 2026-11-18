package com.ev.multiev_charging_management_system.external.ai.timelapse.service;

import com.ev.multiev_charging_management_system.external.ai.timelapse.entity.DashboardTimelapsePeriod;
import com.ev.multiev_charging_management_system.external.ai.timelapse.entity.DashboardTimelapseStationFrame;
import com.ev.multiev_charging_management_system.external.ai.timelapse.repository.DashboardTimelapsePeriodRepository;
import com.ev.multiev_charging_management_system.external.ai.timelapse.repository.DashboardTimelapseStationFrameRepository;
import com.ev.multiev_charging_management_system.external.mqtt.MqttGateway;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.ObjectMapper;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.http.HttpStatus.FORBIDDEN;

@ExtendWith(MockitoExtension.class)
class DashboardTimelapseMqttPublishServiceTest {

    @Mock
    private DashboardTimelapsePeriodRepository periodRepository;

    @Mock
    private DashboardTimelapseStationFrameRepository frameRepository;

    @Mock
    private MqttGateway mqttGateway;

    private DashboardTimelapseMqttPublishService service;

    @BeforeEach
    void setUp() {
        service = new DashboardTimelapseMqttPublishService(
                periodRepository,
                frameRepository,
                mqttGateway,
                new ObjectMapper()
        );
    }

    @Test
    void publishFrameUsesIoTStationTopicByDefault() {
        DashboardTimelapsePeriod period = period();
        DashboardTimelapseStationFrame frame = stationFrame("1", -57.3);
        DashboardTimelapseStationFrame previousFrame = stationFrame("1", -57.3, 74.5);
        when(periodRepository.findByPeriodKey("period-2022-feb")).thenReturn(Optional.of(period));
        when(frameRepository.findByPeriodIdAndFrameIndexOrderByStationIdAsc(null, 327))
                .thenReturn(List.of(frame));
        when(frameRepository.findTopByPeriodIdAndStationIdAndFrameIndexLessThanOrderByFrameIndexDesc(null, "1", 327))
                .thenReturn(Optional.of(previousFrame));

        var response = service.publishFrame("period-2022-feb", 327, "demo", "playback");

        assertEquals("demo", response.mode());
        assertEquals("iot.control", response.topicNamespace());
        assertEquals("ST001", response.commands().get(0).stationId());
        assertEquals("iot.control/stations/ST001/commands", response.commands().get(0).topic());
        verify(mqttGateway).sendToMqtt(
                eq("iot.control/stations/ST001/commands"),
                contains("\"share_energy_kwh\":-57.3")
        );
        verify(mqttGateway).sendToMqtt(
                eq("iot.control/stations/ST001/commands"),
                contains("\"ess_action\":-0.01")
        );
        verify(mqttGateway).sendToMqtt(
                eq("iot.control/stations/ST001/commands"),
                contains("\"command\":\"discharge_ess:dashboard_timelapse\"")
        );
    }

    @Test
    void liveTopicIsBlockedUntilExplicitlyEnabled() {
        DashboardTimelapsePeriod period = period();
        DashboardTimelapseStationFrame frame = stationFrame("1", -57.3);
        when(periodRepository.findByPeriodKey("period-2022-feb")).thenReturn(Optional.of(period));
        when(frameRepository.findByPeriodIdAndFrameIndexOrderByStationIdAsc(null, 327))
                .thenReturn(List.of(frame));

        ResponseStatusException exception = assertThrows(
                ResponseStatusException.class,
                () -> service.publishFrame("period-2022-feb", 327, "live", "playback")
        );

        assertEquals(FORBIDDEN, exception.getStatusCode());
        verifyNoInteractions(mqttGateway);
    }

    @Test
    void liveTopicCanBeExplicitlyEnabledForControlledDemo() {
        ReflectionTestUtils.setField(service, "liveTopicEnabled", true);
        DashboardTimelapsePeriod period = period();
        DashboardTimelapseStationFrame frame = stationFrame("1", -57.3);
        when(periodRepository.findByPeriodKey("period-2022-feb")).thenReturn(Optional.of(period));
        when(frameRepository.findByPeriodIdAndFrameIndexOrderByStationIdAsc(null, 327))
                .thenReturn(List.of(frame));

        var response = service.publishFrame("period-2022-feb", 327, "live", "playback");

        assertEquals("live", response.mode());
        assertEquals("iot.control", response.topicNamespace());
        assertEquals("iot.control/stations/ST001/commands", response.commands().get(0).topic());
        verify(mqttGateway).sendToMqtt(
                eq("iot.control/stations/ST001/commands"),
                contains("\"demo\":false")
        );
    }

    private DashboardTimelapsePeriod period() {
        return DashboardTimelapsePeriod.create(
                "period-2022-feb",
                "2022년 2월 테스트",
                LocalDate.parse("2022-02-01"),
                LocalDate.parse("2022-02-28"),
                "테스트",
                "test",
                true
        );
    }

    private DashboardTimelapseStationFrame stationFrame(String stationId, double shareEnergyKwh) {
        return stationFrame(stationId, shareEnergyKwh, 73.5);
    }

    private DashboardTimelapseStationFrame stationFrame(String stationId, double shareEnergyKwh, double essPercent) {
        return DashboardTimelapseStationFrame.create(
                period(),
                327,
                LocalDate.parse("2022-02-14"),
                15,
                stationId,
                "서울 강남 허브",
                "서울 강남구",
                277.3,
                339.3,
                essPercent,
                174.0,
                shareEnergyKwh,
                3,
                12,
                5,
                "수요 여유",
                "전력 송신",
                "남는 PV 공유",
                "예측 기반 운영"
        );
    }
}
