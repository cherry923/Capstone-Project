package com.ev.multiev_charging_management_system.external.weather;

import com.ev.multiev_charging_management_system.external.weather.dto.KmaSolarNwpForecastValue;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

@Slf4j
@Component
public class KmaSolarNwpApiClient {

    private static final int MAX_OUTPUT_COUNT = 6;
    private static final DateTimeFormatter ISSUE_FMT = DateTimeFormatter.ofPattern("yyyyMMddHHmm");
    private static final DateTimeFormatter FORECAST_FMT = DateTimeFormatter.ofPattern("yyyyMMddHH");

    private final RestClient restClient;
    private final String baseUrl;
    private final String authKey;
    private final String defaultNwp;

    public KmaSolarNwpApiClient(
            @Value("${external.weather.kma-solar-nwp.base-url:https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph_sun_nwp_txt}") String baseUrl,
            @Value("${external.weather.kma-solar-nwp.auth-key:${KMA_APIHUB_AUTH_KEY:}}") String authKey,
            @Value("${external.weather.kma-solar-nwp.nwp:KIMG}") String defaultNwp
    ) {
        this.restClient = RestClient.create();
        this.baseUrl = baseUrl;
        this.authKey = authKey;
        this.defaultNwp = defaultNwp;
    }

    public List<KmaSolarNwpForecastValue> getForecast(
            String variable,
            LocalDateTime issuedAtUtc,
            LocalDateTime startUtc,
            LocalDateTime endUtc,
            int intervalHours,
            double latitude,
            double longitude
    ) {
        return getForecast(defaultNwp, variable, issuedAtUtc, startUtc, endUtc, intervalHours, latitude, longitude);
    }

    public List<KmaSolarNwpForecastValue> getForecast(
            String nwp,
            String variable,
            LocalDateTime issuedAtUtc,
            LocalDateTime startUtc,
            LocalDateTime endUtc,
            int intervalHours,
            double latitude,
            double longitude
    ) {
        if (authKey == null || authKey.isBlank()) {
            throw new KmaSolarNwpApiException("KMA APIHub auth key is empty.");
        }
        if (intervalHours <= 0) {
            throw new IllegalArgumentException("intervalHours must be positive.");
        }

        List<KmaSolarNwpForecastValue> result = new ArrayList<>();
        LocalDateTime cursor = startUtc;
        while (!cursor.isAfter(endUtc)) {
            LocalDateTime chunkEnd = cursor.plusHours((long) intervalHours * (MAX_OUTPUT_COUNT - 1));
            if (chunkEnd.isAfter(endUtc)) {
                chunkEnd = endUtc;
            }
            result.addAll(getForecastChunk(nwp, variable, issuedAtUtc, cursor, chunkEnd, intervalHours, latitude, longitude));
            cursor = chunkEnd.plusHours(intervalHours);
        }
        return result;
    }

    private List<KmaSolarNwpForecastValue> getForecastChunk(
            String nwp,
            String variable,
            LocalDateTime issuedAtUtc,
            LocalDateTime startUtc,
            LocalDateTime endUtc,
            int intervalHours,
            double latitude,
            double longitude
    ) {
        String url = baseUrl
                + "?nwp=" + encode(nwp)
                + "&varn=" + encode(variable)
                + "&tm=" + issuedAtUtc.format(ISSUE_FMT)
                + "&tmef1=" + startUtc.format(FORECAST_FMT)
                + "&tmef2=" + endUtc.format(FORECAST_FMT)
                + "&int=" + intervalHours
                + "&lat=" + latitude
                + "&lon=" + longitude
                + "&disp=1"
                + "&authKey=" + encode(authKey);

        log.info("KMA solar NWP API 호출: nwp={}, variable={}, issueUtc={}, startUtc={}, endUtc={}",
                nwp, variable, issuedAtUtc, startUtc, endUtc);

        String body = restClient.get()
                .uri(URI.create(url))
                .retrieve()
                .body(String.class);

        if (body == null || body.isBlank()) {
            throw new KmaSolarNwpApiException("KMA solar NWP API response is empty.");
        }
        return parseTable(body);
    }

    static List<KmaSolarNwpForecastValue> parseTable(String body) {
        if (body.contains("<Error>")) {
            throw new KmaSolarNwpApiException(normalizeError(body));
        }

        List<List<String>> tableRows = body.lines()
                .filter(line -> line.trim().startsWith("|"))
                .map(KmaSolarNwpApiClient::splitTableRow)
                .filter(row -> row.size() >= 5)
                .toList();

        if (tableRows.size() < 2) {
            throw new KmaSolarNwpApiException("KMA solar NWP table response cannot be parsed.");
        }

        List<String> header = tableRows.stream()
                .filter(row -> "TMFC".equalsIgnoreCase(row.get(0)))
                .findFirst()
                .orElseThrow(() -> new KmaSolarNwpApiException("KMA solar NWP table header is missing."));

        List<String> data = tableRows.stream()
                .filter(row -> row.get(0).matches("\\d{10,12}"))
                .findFirst()
                .orElseThrow(() -> new KmaSolarNwpApiException("KMA solar NWP table data row is missing."));

        LocalDateTime issuedAtUtc = parseKmaDateTime(data.get(0));
        String variable = data.get(1);
        Double longitude = parseDouble(data.get(2));
        Double latitude = parseDouble(data.get(3));

        List<KmaSolarNwpForecastValue> values = new ArrayList<>();
        int valueCount = Math.min(header.size(), data.size()) - 4;
        for (int index = 0; index < valueCount; index++) {
            Double value = parseDouble(data.get(index + 4));
            if (value == null) {
                continue;
            }
            values.add(new KmaSolarNwpForecastValue(
                    issuedAtUtc,
                    parseKmaDateTime(header.get(index + 4)),
                    variable,
                    longitude,
                    latitude,
                    value
            ));
        }
        return values;
    }

    private static List<String> splitTableRow(String line) {
        return Arrays.stream(line.split("\\|"))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .toList();
    }

    private static LocalDateTime parseKmaDateTime(String value) {
        if (value.length() == 10) {
            return LocalDateTime.parse(value, FORECAST_FMT);
        }
        if (value.length() == 12) {
            return LocalDateTime.parse(value, ISSUE_FMT);
        }
        throw new KmaSolarNwpApiException("Invalid KMA datetime: " + value);
    }

    private static Double parseDouble(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException exception) {
            return null;
        }
    }

    private static String normalizeError(String body) {
        return body.replaceAll("<[^>]+>", " ")
                .replaceAll("\\s+", " ")
                .trim();
    }

    private static String encode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }
}
