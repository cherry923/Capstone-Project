package com.ev.multiev_charging_management_system.external.ai.dispatch.service;

import com.ev.multiev_charging_management_system.external.ai.AiModuleException;
import com.ev.multiev_charging_management_system.external.ai.AiPredictionClient;
import com.ev.multiev_charging_management_system.external.ai.dispatch.entity.AiDispatchCommand;
import com.ev.multiev_charging_management_system.external.ai.dispatch.entity.AiDispatchRun;
import com.ev.multiev_charging_management_system.external.ai.dispatch.repository.AiDispatchCommandRepository;
import com.ev.multiev_charging_management_system.external.ai.dispatch.repository.AiDispatchRunRepository;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchRequest;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchResponse;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchRunQueryResponse;
import com.ev.multiev_charging_management_system.external.ai.dto.PvPredictionRequest;
import com.ev.multiev_charging_management_system.external.weather.entity.WeatherRawData;
import com.ev.multiev_charging_management_system.external.weather.service.KmaSolarNwpForecastService;
import com.ev.multiev_charging_management_system.external.weather.service.WeatherService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@SpringBootTest
@Transactional
class AiDispatchServiceTest {

    @Autowired
    private AiDispatchService aiDispatchService;

    @Autowired
    private AiDispatchRunRepository dispatchRunRepository;

    @Autowired
    private AiDispatchCommandRepository dispatchCommandRepository;

    @Autowired
    private AiDispatchQueryService aiDispatchQueryService;

    @Autowired
    private ObjectMapper objectMapper;

    @MockitoBean
    private AiPredictionClient aiPredictionClient;

    @MockitoBean
    private KmaSolarNwpForecastService kmaSolarNwpForecastService;

    @MockitoBean
    private WeatherService weatherService;

    @Test
    void dispatch24hPersistsRunProvenanceAndNormalizedCommands() throws Exception {
        AiDispatchRequest request = request("req-dispatch", "2026-05-07");
        AiDispatchResponse response = objectMapper.readValue("""
                {
                  "request_id": "req-dispatch",
                  "code": "SUCCESS",
                  "message": "ok",
                  "model_version": "dispatch-flow-v1",
                  "data": {
                    "target_date": "2026-05-07",
                    "forecasts": {
                      "source": {
                        "pv": "daylight_fallback",
                        "ev": "/tmp/ev_hybrid_calendar_24h_blend_sac_payload.json",
                        "team_decision_model": "/tmp/evcs_api_model_v1_synthetic_MILP_PI_SAC_FULL"
                      }
                    },
                    "model": {
                      "model_name": "evcs_api_model_v1_synthetic_MILP_PI_SAC_FULL",
                      "model_status": "TEAM_MILP_PI_SAC_LOADED"
                    },
                    "dispatch": {
                      "summary": {"command_count": 1},
                      "commands": [
                        {
                          "hour": 0,
                          "station_id": 1,
                          "share_energy_kwh": -120.0,
                          "ess_action": -0.099958,
                          "raw_ess_action": -0.1,
                          "pv_priority": 1.0,
                          "soc_before": 0.55,
                          "soc_after": 0.450042,
                          "grid_total_kwh": 12.5,
                          "grid_cost": 1875.0,
                          "safety_adjusted": true,
                          "command": "discharge_ess:pv_to_ess_first"
                        }
                      ]
                    }
                  }
                }
                """, AiDispatchResponse.class);
        when(aiPredictionClient.dispatch24h(argThat(value -> "req-dispatch".equals(value.getRequestId()))))
                .thenReturn(response);

        AiDispatchResponse result = aiDispatchService.dispatch24h(request);

        assertEquals("SUCCESS", result.getCode());

        List<AiDispatchRun> runs = dispatchRunRepository.findAll();
        assertEquals(1, runs.size());
        AiDispatchRun run = runs.get(0);
        assertEquals("req-dispatch", run.getRequestId());
        assertEquals(LocalDate.parse("2026-05-07"), run.getTargetDate());
        assertEquals("SUCCESS", run.getStatus());
        assertEquals("dispatch-flow-v1", run.getModelVersion());
        assertEquals("evcs_api_model_v1_synthetic_MILP_PI_SAC_FULL", run.getModelName());
        assertEquals("TEAM_MILP_PI_SAC_LOADED", run.getModelStatus());
        assertEquals("daylight_fallback", run.getPvSource());
        assertEquals(1, run.getCommandCount());
        assertTrue(run.getRequestPayload().contains("\"request_id\":\"req-dispatch\""));
        assertTrue(run.getResponsePayload().contains("\"model_status\":\"TEAM_MILP_PI_SAC_LOADED\""));

        List<AiDispatchCommand> commands = dispatchCommandRepository.findAll();
        assertEquals(1, commands.size());
        AiDispatchCommand command = commands.get(0);
        assertEquals(run.getId(), command.getDispatchRun().getId());
        assertEquals(0, command.getCommandIndex());
        assertEquals(0, command.getHour());
        assertEquals("1", command.getStationId());
        assertEquals(-120.0, command.getShareEnergyKwh());
        assertEquals(-0.099958, command.getEssAction());
        assertEquals(1.0, command.getPvPriority());
        assertEquals("discharge_ess:pv_to_ess_first", command.getCommand());
        assertEquals(Boolean.TRUE, command.getSafetyAdjusted());
        assertTrue(command.getCommandPayload().contains("\"pv_priority\":1.0"));

        AiDispatchRunQueryResponse.Detail latestRun = aiDispatchQueryService.latestRun();
        assertEquals(run.getId(), latestRun.run().runId());
        assertEquals("req-dispatch", latestRun.run().requestId());
        assertEquals(1, latestRun.commands().size());
        assertEquals("1", latestRun.commands().get(0).stationId());
        assertEquals(1.0, latestRun.commands().get(0).pvPriority());
    }

    @Test
    void dispatch24hPersistsAiFailureBodyBeforeRethrowing() throws Exception {
        AiDispatchRequest request = request("req-dispatch", "bad-date");
        AiDispatchResponse response = objectMapper.readValue("""
                {
                  "request_id": "req-dispatch",
                  "code": "INVALID_INPUT_VALUE",
                  "message": "target_date must be YYYY-MM-DD",
                  "model_version": "dispatch-flow-v1",
                  "data": null
                }
                """, AiDispatchResponse.class);
        when(aiPredictionClient.dispatch24h(argThat(value -> "req-dispatch".equals(value.getRequestId()))))
                .thenThrow(new AiModuleException("AI dispatch failed", response));

        assertThrows(AiModuleException.class, () -> aiDispatchService.dispatch24h(request));

        List<AiDispatchRun> runs = dispatchRunRepository.findAll();
        assertEquals(1, runs.size());
        AiDispatchRun run = runs.get(0);
        assertEquals("req-dispatch", run.getRequestId());
        assertEquals("INVALID_INPUT_VALUE", run.getStatus());
        assertEquals("target_date must be YYYY-MM-DD", run.getMessage());
        assertEquals(0, dispatchCommandRepository.count());
    }

    @Test
    void dispatch24hPersistsTransportFailureWithoutAiBodyBeforeRethrowing() {
        AiDispatchRequest request = request("req-dispatch", "2026-05-07");
        when(aiPredictionClient.dispatch24h(argThat(value -> "req-dispatch".equals(value.getRequestId()))))
                .thenThrow(new AiModuleException("AI dispatch 모듈 호출에 실패했습니다."));

        assertThrows(AiModuleException.class, () -> aiDispatchService.dispatch24h(request));

        List<AiDispatchRun> runs = dispatchRunRepository.findAll();
        assertEquals(1, runs.size());
        AiDispatchRun run = runs.get(0);
        assertEquals("req-dispatch", run.getRequestId());
        assertEquals(LocalDate.parse("2026-05-07"), run.getTargetDate());
        assertEquals("AI_MODULE_ERROR", run.getStatus());
        assertEquals("AI dispatch 모듈 호출에 실패했습니다.", run.getMessage());
        assertEquals(0, run.getCommandCount());
        assertEquals(0, dispatchCommandRepository.count());
    }

    @Test
    void dispatch24hCanEnrichMissingPvWeatherFromKmaForecast() throws Exception {
        AiDispatchRequest request = request("req-dispatch-kma", "2026-05-12");
        request.setUseKmaForecastWeather(true);
        request.setForecastLatitude(33.499621);
        request.setForecastLongitude(126.531188);
        request.setNwpIssuedAtUtc("2026-05-11T00:00:00");

        when(kmaSolarNwpForecastService.buildPvEncoderWeather24h(
                LocalDate.parse("2026-05-12"),
                33.499621,
                126.531188,
                LocalDateTime.parse("2026-05-11T00:00:00")
        )).thenReturn(List.of(weatherRow(0)));
        when(weatherService.toDecoderPv(
                eq(LocalDate.parse("2026-05-11")),
                eq("제주도"),
                eq("KPX_REGIONAL_HOURLY_SOLAR_WIND"),
                eq("태양광")
        )).thenReturn(List.of(PvPredictionRequest.PvHourly.builder().hour(0).pvPower(7.0).build()));

        AiDispatchResponse response = objectMapper.readValue("""
                {
                  "request_id": "req-dispatch-kma",
                  "code": "SUCCESS",
                  "message": "ok",
                  "model_version": "dispatch-flow-v1",
                  "data": {
                    "target_date": "2026-05-12",
                    "dispatch": {"summary": {"command_count": 0}, "commands": []}
                  }
                }
                """, AiDispatchResponse.class);
        when(aiPredictionClient.dispatch24h(argThat(value ->
                "2026-05-11".equals(value.getBaseDate())
                        && value.getEncoderWeather24h() != null
                        && value.getDecoderPv24h() != null
        ))).thenReturn(response);

        AiDispatchResponse result = aiDispatchService.dispatch24h(request);

        assertEquals("SUCCESS", result.getCode());
        verify(aiPredictionClient).dispatch24h(argThat(value ->
                value.getEncoderWeather24h().toString().contains("\"temperature\":22.0")
                        && value.getDecoderPv24h().toString().contains("\"pv_power\":7.0")
        ));
    }

    @Test
    void dispatch24hCanEnrichMissingPvWeatherFromStoredAsosActuals() throws Exception {
        AiDispatchRequest request = request("req-dispatch-asos", "2023-12-31");
        request.setUseAsosActualWeather(true);
        request.setAsosStationId(184);
        request.setPvRegion("서울시");

        LocalDate targetDate = LocalDate.parse("2023-12-31");
        LocalDate baseDate = LocalDate.parse("2023-12-30");
        when(weatherService.getDaily(targetDate, 184)).thenReturn(weatherRows(targetDate, 24));
        when(weatherService.getEncoderWindow(baseDate, 184)).thenReturn(weatherRows(baseDate.minusDays(6), 168));
        when(weatherService.toEncoderWeather(argThat(rows -> rows.size() == 24)))
                .thenReturn(weatherRowsForAi(24));
        when(weatherService.toEncoderWeather168h(argThat(rows -> rows.size() == 168)))
                .thenReturn(weatherRowsForAi(168));
        when(weatherService.toDecoderPv(
                eq(baseDate),
                eq("서울시"),
                eq("KPX_REGIONAL_HOURLY_SOLAR_WIND"),
                eq("태양광")
        )).thenReturn(List.of(PvPredictionRequest.PvHourly.builder().hour(0).pvPower(5.5).build()));

        AiDispatchResponse response = objectMapper.readValue("""
                {
                  "request_id": "req-dispatch-asos",
                  "code": "SUCCESS",
                  "message": "ok",
                  "model_version": "dispatch-flow-v1",
                  "data": {
                    "target_date": "2023-12-31",
                    "forecasts": {"source": {"pv": "han_tft_pv"}},
                    "dispatch": {"summary": {"command_count": 0}, "commands": []}
                  }
                }
                """, AiDispatchResponse.class);
        when(aiPredictionClient.dispatch24h(argThat(value ->
                "2023-12-30".equals(value.getBaseDate())
                        && value.getEncoderWeather24h() != null
                        && value.getEncoderWeather168h() != null
                        && value.getFutureWeather24h() != null
                        && value.getDecoderWeather24h() != null
                        && value.getDecoderPv24h() != null
        ))).thenReturn(response);

        AiDispatchResponse result = aiDispatchService.dispatch24h(request);

        assertEquals("SUCCESS", result.getCode());
        verify(aiPredictionClient).dispatch24h(argThat(value ->
                value.getEncoderWeather24h().toString().contains("\"temperature\":22.0")
                        && value.getEncoderWeather168h().toString().contains("\"temperature\":22.0")
                        && value.getFutureWeather24h().toString().contains("\"radiation\":2.0")
                        && value.getDecoderPv24h().toString().contains("\"pv_power\":5.5")
        ));
    }

    private AiDispatchRequest request(String requestId, String targetDate) {
        AiDispatchRequest request = new AiDispatchRequest();
        request.setRequestId(requestId);
        request.setTargetDate(targetDate);
        request.setUseTeamModel(true);
        request.setInitSoc(List.of(0.55, 0.5, 0.45));
        return request;
    }

    private PvPredictionRequest.WeatherHourly weatherRow(int hour) {
        return PvPredictionRequest.WeatherHourly.builder()
                .hour(hour)
                .temperature(22.0)
                .rain(0.0)
                .humidity(60.0)
                .snow(0.0)
                .cloud(4.0)
                .duration(1.0)
                .radiation(2.0)
                .day(132)
                .build();
    }

    private List<WeatherRawData> weatherRows(LocalDate startDate, int hours) {
        return java.util.stream.IntStream.range(0, hours)
                .mapToObj(index -> WeatherRawData.builder()
                        .asosStationId(184)
                        .observationTime(startDate.atStartOfDay().plusHours(index))
                        .temperature(22.0)
                        .rainfall(0.0)
                        .humidity(60.0)
                        .snowfall(0.0)
                        .cloudCover(4.0)
                        .sunshineDuration(1.0)
                        .solarRadiation(2.0)
                        .build())
                .toList();
    }

    private List<PvPredictionRequest.WeatherHourly> weatherRowsForAi(int hours) {
        return java.util.stream.IntStream.range(0, hours)
                .mapToObj(index -> weatherRow(index % 24))
                .toList();
    }
}
