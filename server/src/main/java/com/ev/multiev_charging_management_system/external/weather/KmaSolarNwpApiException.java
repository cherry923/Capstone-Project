package com.ev.multiev_charging_management_system.external.weather;

public class KmaSolarNwpApiException extends RuntimeException {

    public KmaSolarNwpApiException(String message) {
        super(message);
    }

    public KmaSolarNwpApiException(String message, Throwable cause) {
        super(message, cause);
    }
}
