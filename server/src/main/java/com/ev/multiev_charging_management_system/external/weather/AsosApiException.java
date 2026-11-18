package com.ev.multiev_charging_management_system.external.weather;

public class AsosApiException extends RuntimeException {

    public AsosApiException(String message) {
        super(message);
    }

    public AsosApiException(String message, Throwable cause) {
        super(message, cause);
    }
}
