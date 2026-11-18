package com.ev.multiev_charging_management_system.external.ai.controller;

import com.ev.multiev_charging_management_system.external.ai.AiModuleException;
import com.ev.multiev_charging_management_system.external.ai.dispatch.service.AiDispatchQueryService;
import com.ev.multiev_charging_management_system.external.ai.dispatch.service.AiDispatchService;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchResponse;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchRunQueryResponse;
import com.ev.multiev_charging_management_system.external.ai.handler.AiModuleExceptionHandler;
import com.ev.multiev_charging_management_system.config.SecurityConfig;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.ObjectMapper;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.Mockito.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(AiDispatchController.class)
@Import({AiModuleExceptionHandler.class, SecurityConfig.class})
@TestPropertySource(properties = "external.ai.dispatch.demo-open-enabled=true")
class AiDispatchControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockitoBean
    private AiDispatchService aiDispatchService;

    @MockitoBean
    private AiDispatchQueryService aiDispatchQueryService;

    @Test
    void dispatch24hIsDemoCallableAndReturnsAiResponse() throws Exception {
        AiDispatchResponse aiResponse = objectMapper.readValue("""
                {
                  "request_id": "req-dispatch",
                  "code": "SUCCESS",
                  "message": "ok",
                  "model_version": "dispatch-flow-v1",
                  "data": {
                    "forecasts": {"source": {"pv": "han_tft_pv"}},
                    "dispatch": {
                      "summary": {"command_count": 72},
                      "commands": [{"hour": 0, "station_id": 1, "pv_priority": 1.0}]
                    }
                  }
                }
                """, AiDispatchResponse.class);
        when(aiDispatchService.dispatch24h(argThat(request -> "req-dispatch".equals(request.getRequestId()))))
                .thenReturn(aiResponse);

        mockMvc.perform(post("/api/v1/ai/dispatch-24h")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "request_id": "req-dispatch",
                                  "target_date": "2026-05-07",
                                  "use_team_model": false,
                                  "init_soc": [0.55, 0.5, 0.45]
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value("SUCCESS"))
                .andExpect(jsonPath("$.data.forecasts.source.pv").value("han_tft_pv"))
                .andExpect(jsonPath("$.data.dispatch.summary.command_count").value(72))
                .andExpect(jsonPath("$.data.dispatch.commands[0].pv_priority").value(1.0));

        verify(aiDispatchService).dispatch24h(argThat(request ->
                "req-dispatch".equals(request.getRequestId())
                        && "2026-05-07".equals(request.getTargetDate())
                        && Boolean.FALSE.equals(request.getUseTeamModel())
                        && request.getInitSoc().size() == 3
        ));
    }

    @Test
    void dispatch24hMapsAiBusinessFailureToBadGateway() throws Exception {
        AiDispatchResponse aiResponse = objectMapper.readValue("""
                {
                  "request_id": "req-dispatch",
                  "code": "INVALID_INPUT_VALUE",
                  "message": "target_date must be YYYY-MM-DD",
                  "model_version": "dispatch-flow-v1",
                  "data": null
                }
                """, AiDispatchResponse.class);
        when(aiDispatchService.dispatch24h(argThat(request -> "req-dispatch".equals(request.getRequestId()))))
                .thenThrow(new AiModuleException("AI dispatch failed", aiResponse));

        mockMvc.perform(post("/api/v1/ai/dispatch-24h")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "request_id": "req-dispatch",
                                  "target_date": "bad-date"
                                }
                                """))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.code").value("INVALID_INPUT_VALUE"))
                .andExpect(jsonPath("$.message").value("target_date must be YYYY-MM-DD"));
    }

    @Test
    void recentDispatchRunsReturnsStoredSummariesForFrontend() throws Exception {
        when(aiDispatchQueryService.recentRuns(eq(2))).thenReturn(List.of(summary()));

        mockMvc.perform(get("/api/v1/ai/dispatch-runs")
                        .param("limit", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.request_id").doesNotExist())
                .andExpect(jsonPath("$.code").value("SUCCESS"))
                .andExpect(jsonPath("$.message").value("AI dispatch 실행 이력 조회가 정상적으로 완료되었습니다."))
                .andExpect(jsonPath("$.model_version").doesNotExist())
                .andExpect(jsonPath("$.data[0].run_id").value(1))
                .andExpect(jsonPath("$.data[0].request_id").value("req-dispatch"))
                .andExpect(jsonPath("$.data[0].target_date").value("2026-05-07"))
                .andExpect(jsonPath("$.data[0].command_count").value(72))
                .andExpect(jsonPath("$.data[0].pv_source").value("daylight_fallback"));
    }

    @Test
    void latestDispatchRunReturnsCommandsAndOriginalPayload() throws Exception {
        when(aiDispatchQueryService.latestRun()).thenReturn(new AiDispatchRunQueryResponse.Detail(
                summary(),
                List.of(new AiDispatchRunQueryResponse.Command(
                        0, 0, "1", -120.0, -0.099958, -0.1,
                        1.0, 0.55, 0.450042, 12.5, 1875.0,
                        "discharge_ess:pv_to_ess_first", true,
                        objectMapper.readTree("""
                                {"hour":0,"station_id":1,"pv_priority":1.0}
                                """)
                )),
                objectMapper.readTree("""
                        {"request_id":"req-dispatch"}
                        """),
                objectMapper.readTree("""
                        {"code":"SUCCESS","data":{"dispatch":{"summary":{"command_count":72}}}}
                        """)
        ));

        mockMvc.perform(get("/api/v1/ai/dispatch-runs/latest"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.request_id").value("req-dispatch"))
                .andExpect(jsonPath("$.code").value("SUCCESS"))
                .andExpect(jsonPath("$.message").value("ok"))
                .andExpect(jsonPath("$.model_version").value("dispatch-flow-v1"))
                .andExpect(jsonPath("$.data.run.run_id").value(1))
                .andExpect(jsonPath("$.data.commands[0].station_id").value("1"))
                .andExpect(jsonPath("$.data.commands[0].pv_priority").value(1.0))
                .andExpect(jsonPath("$.data.response_payload.code").value("SUCCESS"));
    }

    private AiDispatchRunQueryResponse.Summary summary() {
        return new AiDispatchRunQueryResponse.Summary(
                1L,
                "req-dispatch",
                LocalDate.parse("2026-05-07"),
                "SUCCESS",
                "ok",
                "dispatch-flow-v1",
                "upper_lower_rule_fallback",
                "FALLBACK_REQUESTED",
                "daylight_fallback",
                "/tmp/ev_payload.json",
                "/tmp/team_model",
                72,
                LocalDateTime.parse("2026-05-12T12:00:00")
        );
    }
}
