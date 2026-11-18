package com.ev.multiev_charging_management_system.external.ai.timelapse.controller;

import com.ev.multiev_charging_management_system.config.SecurityConfig;
import com.ev.multiev_charging_management_system.external.ai.handler.AiModuleExceptionHandler;
import com.ev.multiev_charging_management_system.external.ai.timelapse.dto.DashboardTimelapseMqttPublishResponse;
import com.ev.multiev_charging_management_system.external.ai.timelapse.dto.DashboardTimelapseResponse;
import com.ev.multiev_charging_management_system.external.ai.timelapse.dto.DashboardTimelapseUpsertRequest;
import com.ev.multiev_charging_management_system.external.ai.timelapse.service.DashboardTimelapseMqttPublishService;
import com.ev.multiev_charging_management_system.external.ai.timelapse.service.DashboardTimelapsePeriodService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(DashboardTimelapsePeriodController.class)
@Import({AiModuleExceptionHandler.class, SecurityConfig.class})
@TestPropertySource(properties = "external.ai.dispatch.demo-open-enabled=true")
class DashboardTimelapsePeriodControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private DashboardTimelapsePeriodService timelapsePeriodService;

    @MockitoBean
    private DashboardTimelapseMqttPublishService timelapseMqttPublishService;

    @Test
    void latestPeriodReturnsStoredFramesForDashboard() throws Exception {
        when(timelapsePeriodService.latestActivePeriod()).thenReturn(detail());

        mockMvc.perform(get("/api/v1/ai/timelapse-periods/latest"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value("SUCCESS"))
                .andExpect(jsonPath("$.data.period_key").value("period-2022-jan-feb"))
                .andExpect(jsonPath("$.data.label").value("2022년 1-2월 테스트"))
                .andExpect(jsonPath("$.data.frames[0].frame_index").value(0))
                .andExpect(jsonPath("$.data.frames[0].frame_date").value("2022-01-01"))
                .andExpect(jsonPath("$.data.frames[0].hour").value(9))
                .andExpect(jsonPath("$.data.frames[0].stations[0].station_id").value("1"))
                .andExpect(jsonPath("$.data.frames[0].stations[0].demand_kwh").value(232.0))
                .andExpect(jsonPath("$.data.frames[0].stations[0].pv_kw").value(92.0))
                .andExpect(jsonPath("$.data.frames[0].stations[0].ess_percent").value(74.0));
    }

    @Test
    void specificPeriodReturnsStoredFramesForDashboard() throws Exception {
        when(timelapsePeriodService.getPeriod("period-2022-jan-feb")).thenReturn(detail());

        mockMvc.perform(get("/api/v1/ai/timelapse-periods/period-2022-jan-feb"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value("SUCCESS"))
                .andExpect(jsonPath("$.data.period_key").value("period-2022-jan-feb"))
                .andExpect(jsonPath("$.data.frames[0].stations[0].policy_text").value("ESS 74% 유지"));
    }

    @Test
    void upsertPeriodIsDemoCallableAndReturnsCreatedDetail() throws Exception {
        when(timelapsePeriodService.upsertPeriod(argThat(request ->
                "period-2022-jan-feb".equals(request.periodKey())
                        && request.frames().size() == 1
                        && request.frames().get(0).stations().size() == 1
        ))).thenReturn(detail());

        mockMvc.perform(post("/api/v1/ai/timelapse-periods")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "period_key": "period-2022-jan-feb",
                                  "label": "2022년 1-2월 테스트",
                                  "start_date": "2022-01-01",
                                  "end_date": "2022-02-28",
                                  "description": "프론트 타임랩스 테스트",
                                  "source": "test",
                                  "active": true,
                                  "frames": [
                                    {
                                      "hour": 9,
                                      "stations": [
                                        {
                                          "station_id": "1",
                                          "station_name": "서울 강남 허브",
                                          "region": "서울 강남구",
                                          "demand_kwh": 232.0,
                                          "pv_kw": 92.0,
                                          "ess_percent": 74.0,
                                          "tariff_krw_per_kwh": 118.0,
                                          "share_energy_kwh": -12.0,
                                          "active_chargers": 11,
                                          "total_chargers": 12,
                                          "vehicle_count": 17,
                                          "status": "정상",
                                          "command_text": "전력 송신",
                                          "policy_text": "ESS 74% 유지",
                                          "prediction_text": "예측 기반 운영"
                                        }
                                      ]
                                    }
                                  ]
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.code").value("SUCCESS"))
                .andExpect(jsonPath("$.data.period_key").value("period-2022-jan-feb"));

        verify(timelapsePeriodService).upsertPeriod(argThat(request ->
                "period-2022-jan-feb".equals(request.periodKey())
                        && LocalDate.parse("2022-01-01").equals(request.startDate())
                        && request.frames().get(0).hour() == 9
        ));
    }

    @Test
    void publishFrameToMqttIsDemoCallableAndUsesIoTStationTopic() throws Exception {
        when(timelapseMqttPublishService.publishFrame("period-2022-jan-feb", 327, "demo", "playback"))
                .thenReturn(new DashboardTimelapseMqttPublishResponse(
                        "period-2022-jan-feb",
                        327,
                        LocalDate.parse("2022-02-14"),
                        15,
                        "demo",
                        "iot.control",
                        LocalDateTime.parse("2026-06-03T16:00:00"),
                        List.of(new DashboardTimelapseMqttPublishResponse.PublishedCommand(
                                "ST001",
                                "iot.control/stations/ST001/commands",
                                Map.of("station_id", "ST001", "source_station_id", "1", "share_energy_kwh", -57.3)
                        ))
                ));

        mockMvc.perform(post("/api/v1/ai/timelapse-periods/period-2022-jan-feb/frames/327/mqtt-publish")
                        .queryParam("trigger", "playback"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value("SUCCESS"))
                .andExpect(jsonPath("$.data.mode").value("demo"))
                .andExpect(jsonPath("$.data.topic_namespace").value("iot.control"))
                .andExpect(jsonPath("$.data.commands[0].station_id").value("ST001"))
                .andExpect(jsonPath("$.data.commands[0].topic").value("iot.control/stations/ST001/commands"));

        verify(timelapseMqttPublishService).publishFrame("period-2022-jan-feb", 327, "demo", "playback");
    }

    private DashboardTimelapseResponse.Detail detail() {
        return new DashboardTimelapseResponse.Detail(
                "period-2022-jan-feb",
                "2022년 1-2월 테스트",
                LocalDate.parse("2022-01-01"),
                LocalDate.parse("2022-02-28"),
                "프론트 타임랩스 테스트",
                "test",
                List.of(new DashboardTimelapseResponse.Frame(
                        0,
                        LocalDate.parse("2022-01-01"),
                        9,
                        List.of(new DashboardTimelapseResponse.StationFrame(
                                "1",
                                "서울 강남 허브",
                                "서울 강남구",
                                232.0,
                                92.0,
                                74.0,
                                118.0,
                                -12.0,
                                11,
                                12,
                                17,
                                "정상",
                                "전력 송신",
                                "ESS 74% 유지",
                                "예측 기반 운영"
                        ))
                ))
        );
    }
}
