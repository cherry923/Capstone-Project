package com.ev.multiev_charging_management_system.external.weather.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

@Getter
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class AsosResponse {

    private Response response;

    @Getter
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Response {
        private Header header;
        private Body body;
    }

    @Getter
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Header {
        private String resultCode;
        private String resultMsg;
    }

    @Getter
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Body {
        private String dataType;
        private Items items;
        private int pageNo;
        private int numOfRows;
        private int totalCount;
    }

    @Getter
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Items {
        private List<Item> item;
    }

    @Getter
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Item {
        private String tm;           // 일시 "2024-01-01 00:00"
        private String stnId;        // 관측소 코드
        private String stnNm;        // 관측소명
        private String ta;           // 기온 (°C)
        private String rn;           // 강수량 (mm)
        private String ws;           // 풍속 (m/s)
        private String wd;           // 풍향
        private String hm;           // 습도 (%)
        private String ss;           // 일조시간 (hr)
        private String icsr;         // 일사량 (MJ/m²)
        private String dsnw;         // 적설 (cm)
        private String dc10Tca;      // 전운량 (10분위)
    }
}
