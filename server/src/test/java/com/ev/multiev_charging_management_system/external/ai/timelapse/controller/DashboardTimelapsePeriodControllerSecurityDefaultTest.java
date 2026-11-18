package com.ev.multiev_charging_management_system.external.ai.timelapse.controller;

import com.ev.multiev_charging_management_system.config.SecurityConfig;
import com.ev.multiev_charging_management_system.external.ai.handler.AiModuleExceptionHandler;
import com.ev.multiev_charging_management_system.external.ai.timelapse.dto.DashboardTimelapseResponse;
import com.ev.multiev_charging_management_system.external.ai.timelapse.service.DashboardTimelapseMqttPublishService;
import com.ev.multiev_charging_management_system.external.ai.timelapse.service.DashboardTimelapsePeriodService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDate;
import java.util.List;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(DashboardTimelapsePeriodController.class)
@Import({AiModuleExceptionHandler.class, SecurityConfig.class})
class DashboardTimelapsePeriodControllerSecurityDefaultTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private DashboardTimelapsePeriodService timelapsePeriodService;

    @MockitoBean
    private DashboardTimelapseMqttPublishService timelapseMqttPublishService;

    @Test
    void latestPeriodIsOpenForDashboardByDefault() throws Exception {
        when(timelapsePeriodService.latestActivePeriod()).thenReturn(new DashboardTimelapseResponse.Detail(
                "period-2022-jan-feb",
                "2022년 1-2월 테스트",
                LocalDate.parse("2022-01-01"),
                LocalDate.parse("2022-02-28"),
                "프론트 타임랩스 테스트",
                "test",
                List.of()
        ));

        mockMvc.perform(get("/api/v1/ai/timelapse-periods/latest"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value("SUCCESS"))
                .andExpect(jsonPath("$.data.period_key").value("period-2022-jan-feb"));
    }

    @Test
    void upsertPeriodIsNotOpenByDefault() throws Exception {
        mockMvc.perform(post("/api/v1/ai/timelapse-periods")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "period_key": "period-2022-jan-feb",
                                  "label": "2022년 1-2월 테스트",
                                  "start_date": "2022-01-01",
                                  "end_date": "2022-02-28",
                                  "frames": []
                                }
                                """))
                .andExpect(status().isForbidden());
    }

    @Test
    void publishFrameToMqttIsNotOpenByDefault() throws Exception {
        mockMvc.perform(post("/api/v1/ai/timelapse-periods/period-2022-jan-feb/frames/327/mqtt-publish")
                        .queryParam("mode", "live")
                        .queryParam("trigger", "playback"))
                .andExpect(status().isForbidden());
    }
}
