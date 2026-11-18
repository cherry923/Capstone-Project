package com.ev.multiev_charging_management_system.mqtt.controller;

import com.ev.multiev_charging_management_system.config.SecurityConfig;
import com.ev.multiev_charging_management_system.mqtt.dto.ChargerMeasurementResponse;
import com.ev.multiev_charging_management_system.mqtt.service.ChargerMeasurementResponseService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDateTime;
import java.util.List;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ChargerMeasurementController.class)
@Import(SecurityConfig.class)
@TestPropertySource(properties = "app.cors.allowed-origins=http://127.0.0.1:4177")
class ChargerMeasurementControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private ChargerMeasurementResponseService queryService;

    @Test
    void latestSnapshotIsCallableWithoutAiDemoOpenFlag() throws Exception {
        when(queryService.getLatestSnapshot()).thenReturn(List.of(measurement()));

        mockMvc.perform(get("/api/chargers/measurements/latest-snapshot"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value(10))
                .andExpect(jsonPath("$[0].stationId").value("1"))
                .andExpect(jsonPath("$[0].chargerNo").value(2))
                .andExpect(jsonPath("$[0].charging").value(true))
                .andExpect(jsonPath("$[0].essRemain").value(0.73));
    }

    @Test
    void latestSnapshotAlsoSupportsVersionedApiPath() throws Exception {
        when(queryService.getLatestSnapshot()).thenReturn(List.of(measurement()));

        mockMvc.perform(get("/api/v1/chargers/measurements/latest-snapshot"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].stationId").value("1"));
    }

    @Test
    void chargerMeasurementCorsAllowsFrontendPreviewPort() throws Exception {
        mockMvc.perform(options("/api/chargers/measurements/latest-snapshot")
                        .header(HttpHeaders.ORIGIN, "http://127.0.0.1:4177")
                        .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "GET"))
                .andExpect(status().isOk())
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "http://127.0.0.1:4177"));
    }

    private ChargerMeasurementResponse measurement() {
        return ChargerMeasurementResponse.builder()
                .id(10L)
                .stationId("1")
                .chargerNo(2)
                .charging(true)
                .power(42)
                .voltage(220.0)
                .current(14.0)
                .essRemain(0.73)
                .measuredAt(LocalDateTime.parse("2026-05-14T10:00:00"))
                .receivedAt(LocalDateTime.parse("2026-05-14T10:00:01"))
                .build();
    }
}
