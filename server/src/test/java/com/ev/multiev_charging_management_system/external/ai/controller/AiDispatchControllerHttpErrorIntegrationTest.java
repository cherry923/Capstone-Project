package com.ev.multiev_charging_management_system.external.ai.controller;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpStatus;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;

@SpringBootTest(
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "external.ai.dispatch.demo-open-enabled=true"
)
class AiDispatchControllerHttpErrorIntegrationTest {

    private static HttpServer aiServer;

    @Value("${local.server.port}")
    private int port;

    @Autowired
    private ObjectMapper objectMapper;

    @DynamicPropertySource
    static void registerProperties(DynamicPropertyRegistry registry) {
        ensureAiServerStarted();
        registry.add("external.ai.base-url", () -> "http://127.0.0.1:" + aiServer.getAddress().getPort());
    }

    @AfterAll
    static void tearDown() {
        if (aiServer != null) {
            aiServer.stop(0);
        }
    }

    @Test
    void dispatch24hPreservesUpstreamHttpErrorBodyThroughController() throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create("http://127.0.0.1:" + port + "/api/v1/ai/dispatch-24h"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString("""
                        {
                          "request_id": "req-dispatch",
                          "target_date": "bad-date"
                        }
                        """))
                .build();

        HttpResponse<String> response = HttpClient.newHttpClient()
                .send(request, HttpResponse.BodyHandlers.ofString());

        assertEquals(HttpStatus.BAD_GATEWAY.value(), response.statusCode());
        var body = objectMapper.readTree(response.body());
        assertEquals("INVALID_INPUT_VALUE", body.get("code").asText());
        assertEquals("target_date must be YYYY-MM-DD", body.get("message").asText());
    }

    private static void ensureAiServerStarted() {
        if (aiServer != null) {
            return;
        }
        try {
            aiServer = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            aiServer.createContext("/", AiDispatchControllerHttpErrorIntegrationTest::handleAiRequest);
            aiServer.start();
        } catch (IOException e) {
            throw new IllegalStateException("Failed to start AI stub server", e);
        }
    }

    private static void handleAiRequest(HttpExchange exchange) throws IOException {
        byte[] response = """
                {
                  "request_id": "req-dispatch",
                  "code": "INVALID_INPUT_VALUE",
                  "message": "target_date must be YYYY-MM-DD",
                  "model_version": "dispatch-flow-v1",
                  "data": null
                }
                """.getBytes(StandardCharsets.UTF_8);

        exchange.getResponseHeaders().add("Content-Type", "application/json");
        exchange.sendResponseHeaders(422, response.length);
        exchange.getResponseBody().write(response);
        exchange.close();
    }
}
