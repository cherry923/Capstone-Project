package com.ev.multiev_charging_management_system.external.ai.controller;

import com.ev.multiev_charging_management_system.config.SecurityConfig;
import com.ev.multiev_charging_management_system.external.ai.dispatch.service.AiDispatchQueryService;
import com.ev.multiev_charging_management_system.external.ai.dispatch.service.AiDispatchService;
import com.ev.multiev_charging_management_system.external.ai.handler.AiModuleExceptionHandler;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(AiDispatchController.class)
@Import({AiModuleExceptionHandler.class, SecurityConfig.class})
class AiDispatchControllerSecurityDefaultTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private AiDispatchService aiDispatchService;

    @MockitoBean
    private AiDispatchQueryService aiDispatchQueryService;

    @Test
    void dispatch24hIsNotOpenByDefault() throws Exception {
        mockMvc.perform(post("/api/v1/ai/dispatch-24h")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "request_id": "req-dispatch",
                                  "target_date": "2026-05-07"
                                }
                                """))
                .andExpect(status().isForbidden());
    }
}
