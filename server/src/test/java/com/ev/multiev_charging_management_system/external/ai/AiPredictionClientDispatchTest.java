package com.ev.multiev_charging_management_system.external.ai;

import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchRequest;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchResponse;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;

class AiPredictionClientDispatchTest {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final AtomicReference<String> requestPath = new AtomicReference<>();
    private final AtomicReference<String> requestBody = new AtomicReference<>();

    private HttpServer server;
    private String responseJson;
    private int responseStatus;
    private AiPredictionClient client;

    @BeforeEach
    void setUp() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", this::handle);
        server.setExecutor(Executors.newSingleThreadExecutor());
        server.start();
        responseStatus = 200;
        client = new AiPredictionClient("http://127.0.0.1:" + server.getAddress().getPort(), objectMapper);
    }

    @AfterEach
    void tearDown() {
        server.stop(0);
    }

    @Test
    void dispatch24hPostsToAiFlowEndpointAndPreservesNestedData() throws Exception {
        responseJson = """
                {
                  "request_id": "req-dispatch",
                  "code": "SUCCESS",
                  "message": "ok",
                  "model_version": "dispatch-flow-v1",
                  "data": {
                    "forecasts": {"source": {"pv": "han_tft_pv"}},
                    "dispatch": {
                      "summary": {"command_count": 72},
                      "commands": [{"hour": 0, "station_id": 1, "command": "discharge_ess:pv_to_ev_first"}]
                    }
                  }
                }
                """;

        AiDispatchRequest request = new AiDispatchRequest();
        request.setRequestId("req-dispatch");
        request.setTargetDate("2026-05-07");
        request.setUseTeamModel(false);
        request.setInitSoc(List.of(0.55, 0.5, 0.45));

        AiDispatchResponse response = client.dispatch24h(request);

        assertEquals("/api/v1/ai/flow/dispatch-24h", requestPath.get());
        assertEquals("req-dispatch", objectMapper.readTree(requestBody.get()).get("request_id").asText());
        assertEquals("2026-05-07", objectMapper.readTree(requestBody.get()).get("target_date").asText());
        assertEquals("SUCCESS", response.getCode());
        assertEquals(72, response.getData().at("/dispatch/summary/command_count").asInt());
        assertEquals("han_tft_pv", response.getData().at("/forecasts/source/pv").asText());
        assertEquals("discharge_ess:pv_to_ev_first",
                response.getData().at("/dispatch/commands/0/command").asText());
    }

    @Test
    void dispatch24hThrowsWithAiResponseBodyWhenAiReturnsBusinessFailure() {
        responseJson = """
                {
                  "request_id": "req-dispatch",
                  "code": "INVALID_INPUT_VALUE",
                  "message": "target_date must be YYYY-MM-DD",
                  "model_version": "dispatch-flow-v1",
                  "data": null
                }
                """;

        AiDispatchRequest request = new AiDispatchRequest();
        request.setRequestId("req-dispatch");
        request.setTargetDate("bad-date");

        AiModuleException exception = assertThrows(AiModuleException.class, () -> client.dispatch24h(request));

        AiDispatchResponse responseBody = assertInstanceOf(AiDispatchResponse.class, exception.getResponseBody());
        assertEquals("INVALID_INPUT_VALUE", responseBody.getCode());
        assertEquals("target_date must be YYYY-MM-DD", responseBody.getMessage());
    }

    @Test
    void dispatch24hPreservesAiResponseBodyWhenAiReturnsHttpError() {
        responseStatus = 422;
        responseJson = """
                {
                  "request_id": "req-dispatch",
                  "code": "INVALID_INPUT_VALUE",
                  "message": "target_date must be YYYY-MM-DD",
                  "model_version": "dispatch-flow-v1",
                  "data": null
                }
                """;

        AiDispatchRequest request = new AiDispatchRequest();
        request.setRequestId("req-dispatch");
        request.setTargetDate("bad-date");

        AiModuleException exception = assertThrows(AiModuleException.class, () -> client.dispatch24h(request));

        AiDispatchResponse responseBody = assertInstanceOf(AiDispatchResponse.class, exception.getResponseBody());
        assertEquals("INVALID_INPUT_VALUE", responseBody.getCode());
        assertEquals("target_date must be YYYY-MM-DD", responseBody.getMessage());
    }

    @Test
    void dispatch24hPreservesAiResponseBodyWhenAiReturnsServerError() {
        responseStatus = 503;
        responseJson = """
                {
                  "request_id": "req-dispatch",
                  "code": "AI_MODULE_UNAVAILABLE",
                  "message": "AI module is temporarily unavailable",
                  "model_version": "dispatch-flow-v1",
                  "data": null
                }
                """;

        AiDispatchRequest request = new AiDispatchRequest();
        request.setRequestId("req-dispatch");
        request.setTargetDate("2026-05-07");

        AiModuleException exception = assertThrows(AiModuleException.class, () -> client.dispatch24h(request));

        AiDispatchResponse responseBody = assertInstanceOf(AiDispatchResponse.class, exception.getResponseBody());
        assertEquals("AI_MODULE_UNAVAILABLE", responseBody.getCode());
        assertEquals("AI module is temporarily unavailable", responseBody.getMessage());
    }

    private void handle(HttpExchange exchange) throws IOException {
        requestPath.set(exchange.getRequestURI().getPath());
        requestBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
        byte[] response = responseJson.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().add("Content-Type", "application/json");
        exchange.sendResponseHeaders(responseStatus, response.length);
        exchange.getResponseBody().write(response);
        exchange.close();
    }
}
