package com.ev.multiev_charging_management_system.external.ai;

import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchRequest;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchResponse;
import com.ev.multiev_charging_management_system.external.ai.dto.PvPredictionRequest;
import com.ev.multiev_charging_management_system.external.ai.dto.PvPredictionResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;

@Slf4j
@Component
public class AiPredictionClient {

    private final RestClient restClient;
    private final ObjectMapper objectMapper;

    public AiPredictionClient(
            @Value("${external.ai.base-url}") String baseUrl,
            ObjectMapper objectMapper
    ) {
        this.objectMapper = objectMapper;
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(3_000);
        requestFactory.setReadTimeout(30_000);

        this.restClient = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(requestFactory)
                .build();
    }

    /**
     * AI 예측 모듈에 PV 발전량 예측을 요청한다.
     * POST /api/v1/ai/predictions/pv
     */
    public PvPredictionResponse predictPv(PvPredictionRequest request) {
        log.info("AI PV 예측 요청: stationId={}, baseDate={}",
                request.getStationId(), request.getBaseDate());

        PvPredictionResponse response = restClient.post()
                .uri("/api/v1/ai/predictions/pv")
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(PvPredictionResponse.class);

        if (response == null) {
            throw new AiModuleException("AI 예측 모듈 응답이 null입니다.");
        }

        if (!"SUCCESS".equals(response.getCode())) {
            throw new AiModuleException(
                    "AI 예측 실패: code=" + response.getCode() + ", msg=" + response.getMessage()
            );
        }

        log.info("AI PV 예측 완료: stationId={}, targetDate={}",
                response.getData().getStationId(), response.getData().getTargetDate());
        return response;
    }

    /**
     * AI 모듈에 24시간 다중 충전소 dispatch 흐름 실행을 요청한다.
     * POST /api/v1/ai/flow/dispatch-24h
     */
    public AiDispatchResponse dispatch24h(AiDispatchRequest request) {
        log.info("AI dispatch-24h 요청: requestId={}, targetDate={}",
                request.getRequestId(), request.getTargetDate());

        AiDispatchResponse response;
        try {
            response = restClient.post()
                    .uri("/api/v1/ai/flow/dispatch-24h")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(request)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, (httpRequest, httpResponse) -> {
                        throw dispatchExceptionFromErrorResponse(httpResponse);
                    })
                    .body(AiDispatchResponse.class);
        } catch (RestClientException e) {
            throw new AiModuleException("AI dispatch 모듈 호출에 실패했습니다.", e);
        }

        if (response == null) {
            throw new AiModuleException("AI dispatch 모듈 응답이 null입니다.");
        }

        if (!"SUCCESS".equals(response.getCode())) {
            throw new AiModuleException(
                    "AI dispatch 실패: code=" + response.getCode() + ", msg=" + response.getMessage(),
                    response
            );
        }

        log.info("AI dispatch-24h 완료: requestId={}, modelVersion={}",
                response.getRequestId(), response.getModelVersion());
        return response;
    }

    private AiModuleException dispatchExceptionFromErrorResponse(ClientHttpResponse httpResponse) throws IOException {
        byte[] body = httpResponse.getBody().readAllBytes();
        if (body.length > 0) {
            try {
                AiDispatchResponse responseBody = objectMapper.readValue(body, AiDispatchResponse.class);
                return new AiModuleException(
                        "AI dispatch HTTP 실패: status=" + httpResponse.getStatusCode(),
                        responseBody
                );
            } catch (RuntimeException ignored) {
                // Non-contract upstream errors are still surfaced as transport failures below.
            }
        }

        return new AiModuleException("AI dispatch HTTP 실패: status=" + httpResponse.getStatusCode());
    }
}
