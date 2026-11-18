package com.ev.multiev_charging_management_system.external.ai.handler;

import com.ev.multiev_charging_management_system.external.ai.AiModuleException;
import com.ev.multiev_charging_management_system.external.ai.controller.AiDispatchController;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;

@RestControllerAdvice(assignableTypes = AiDispatchController.class)
public class AiModuleExceptionHandler {

    @ExceptionHandler(AiModuleException.class)
    public ResponseEntity<Object> handleAiModuleException(AiModuleException exception) {
        Object responseBody = exception.getResponseBody();
        if (responseBody != null) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(responseBody);
        }
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(Map.of(
                "code", "AI_MODULE_ERROR",
                "message", exception.getMessage()
        ));
    }
}
