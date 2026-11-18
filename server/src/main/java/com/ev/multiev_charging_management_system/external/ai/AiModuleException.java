package com.ev.multiev_charging_management_system.external.ai;

public class AiModuleException extends RuntimeException {

    private final Object responseBody;

    public AiModuleException(String message) {
        super(message);
        this.responseBody = null;
    }

    public AiModuleException(String message, Throwable cause) {
        super(message, cause);
        this.responseBody = null;
    }

    public AiModuleException(String message, Object responseBody) {
        super(message);
        this.responseBody = responseBody;
    }

    public Object getResponseBody() {
        return responseBody;
    }
}
