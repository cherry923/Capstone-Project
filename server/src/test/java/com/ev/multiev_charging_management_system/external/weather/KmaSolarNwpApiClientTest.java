package com.ev.multiev_charging_management_system.external.weather;

import com.ev.multiev_charging_management_system.external.weather.dto.KmaSolarNwpForecastValue;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class KmaSolarNwpApiClientTest {

    @Test
    void parseTableReadsForecastColumns() {
        String body = """
                ======================================================================
                |     TMFC     |   VAR   |     LON    |    LAT    |  2026051200  |  2026051203  |
                ======================================================================
                |  2026051100  |  DSWRF  |  126.5312  |  33.4996  |       100.9  |       322.3  |
                ======================================================================
                """;

        List<KmaSolarNwpForecastValue> result = KmaSolarNwpApiClient.parseTable(body);

        assertEquals(2, result.size());
        assertEquals(LocalDateTime.of(2026, 5, 11, 0, 0), result.get(0).issuedAtUtc());
        assertEquals(LocalDateTime.of(2026, 5, 12, 0, 0), result.get(0).forecastTimeUtc());
        assertEquals("DSWRF", result.get(0).variable());
        assertEquals(126.5312, result.get(0).longitude());
        assertEquals(33.4996, result.get(0).latitude());
        assertEquals(100.9, result.get(0).value());
        assertEquals(LocalDateTime.of(2026, 5, 12, 3, 0), result.get(1).forecastTimeUtc());
        assertEquals(322.3, result.get(1).value());
    }

    @Test
    void parseTableRejectsKmaErrorBody() {
        assertThrows(KmaSolarNwpApiException.class, () -> KmaSolarNwpApiClient.parseTable("""
                <Error>
                    [정의되지 않은 옵션] varn=
                </Error>
                """));
    }
}
