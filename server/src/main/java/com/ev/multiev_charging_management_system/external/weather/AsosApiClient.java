package com.ev.multiev_charging_management_system.external.weather;

import com.ev.multiev_charging_management_system.external.weather.dto.AsosResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Slf4j
@Component
public class AsosApiClient {

    private final RestClient restClient;
    private final String baseUrl;
    private final String serviceKey;

    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("yyyyMMdd");

    public AsosApiClient(
            @Value("${external.weather.asos.base-url}") String baseUrl,
            @Value("${external.weather.asos.service-key}") String serviceKey
    ) {
        this.restClient = RestClient.create();
        this.baseUrl = baseUrl;
        this.serviceKey = serviceKey;
    }

    /**
     * 특정 날짜의 24시간 기상 관측 데이터를 조회한다.
     * ASOS는 전일(D-1)까지만 제공하며, 전일 자료는 11시 이후 조회 가능하다.
     */
    public List<AsosResponse.Item> getHourlyWeather(LocalDate date, int stationId) {
        String dateStr = date.format(DATE_FMT);
        String encodedKey = URLEncoder.encode(serviceKey, StandardCharsets.UTF_8);

        String fullUrl = baseUrl + "/getWthrDataList"
                + "?ServiceKey=" + encodedKey
                + "&dataType=JSON"
                + "&dataCd=ASOS"
                + "&dateCd=HR"
                + "&startDt=" + dateStr
                + "&startHh=00"
                + "&endDt=" + dateStr
                + "&endHh=23"
                + "&stnIds=" + stationId
                + "&numOfRows=24"
                + "&pageNo=1";

        log.info("ASOS API 호출: date={}, stationId={}", dateStr, stationId);

        AsosResponse response = restClient.get()
                .uri(URI.create(fullUrl))
                .retrieve()
                .body(AsosResponse.class);

        if (response == null || response.getResponse() == null) {
            throw new AsosApiException("ASOS API 응답이 null입니다.");
        }

        AsosResponse.Header header = response.getResponse().getHeader();
        if (!"00".equals(header.getResultCode())) {
            throw new AsosApiException(
                    "ASOS API 오류: code=" + header.getResultCode() + ", msg=" + header.getResultMsg()
            );
        }

        AsosResponse.Body body = response.getResponse().getBody();
        if (body.getItems() == null || body.getItems().getItem() == null) {
            log.warn("ASOS API 데이터 없음: date={}, stationId={}", dateStr, stationId);
            return List.of();
        }

        log.info("ASOS API 조회 완료: {}건", body.getItems().getItem().size());
        return body.getItems().getItem();
    }
}
