package com.ev.multiev_charging_management_system.external.ai.dispatch.service;

import com.ev.multiev_charging_management_system.external.ai.AiModuleException;
import com.ev.multiev_charging_management_system.external.ai.dispatch.entity.AiDispatchCommand;
import com.ev.multiev_charging_management_system.external.ai.dispatch.entity.AiDispatchRun;
import com.ev.multiev_charging_management_system.external.ai.dispatch.repository.AiDispatchCommandRepository;
import com.ev.multiev_charging_management_system.external.ai.dispatch.repository.AiDispatchRunRepository;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchRequest;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class AiDispatchPersistenceService {

    private static final String AI_MODULE_ERROR = "AI_MODULE_ERROR";

    private final AiDispatchRunRepository dispatchRunRepository;
    private final AiDispatchCommandRepository dispatchCommandRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public AiDispatchRun save(AiDispatchRequest request, AiDispatchResponse response) {
        return persist(request, response);
    }

    @Transactional
    public AiDispatchRun saveFailure(AiDispatchRequest request, AiModuleException exception) {
        if (exception.getResponseBody() instanceof AiDispatchResponse response) {
            return persist(request, response);
        }

        AiDispatchRun run = AiDispatchRun.builder()
                .requestId(request.getRequestId())
                .targetDate(parseTargetDate(request.getTargetDate()))
                .status(AI_MODULE_ERROR)
                .message(exception.getMessage())
                .commandCount(0)
                .requestPayload(toJson(request))
                .build();
        return dispatchRunRepository.save(run);
    }

    private AiDispatchRun persist(AiDispatchRequest request, AiDispatchResponse response) {
        JsonNode data = response.getData();
        AiDispatchRun run = AiDispatchRun.builder()
                .requestId(firstNonBlank(response.getRequestId(), request.getRequestId()))
                .targetDate(parseTargetDate(firstNonBlank(textAt(data, "/target_date"), request.getTargetDate())))
                .status(firstNonBlank(response.getCode(), AI_MODULE_ERROR))
                .message(response.getMessage())
                .modelVersion(response.getModelVersion())
                .modelName(firstTextAt(data, "/model/model_name", "/model_source/model_name"))
                .modelStatus(firstTextAt(data, "/model/model_status", "/model_source/model_status"))
                .pvSource(firstTextAt(data, "/forecasts/source/pv", "/forecast_source/pv"))
                .evSource(firstTextAt(data, "/forecasts/source/ev", "/forecast_source/ev"))
                .teamModelSource(firstTextAt(data,
                        "/forecasts/source/team_decision_model",
                        "/forecast_source/team_decision_model"))
                .commandCount(integerAt(data, "/dispatch/summary/command_count"))
                .requestPayload(toJson(request))
                .responsePayload(toJson(response))
                .build();

        AiDispatchRun savedRun = dispatchRunRepository.save(run);
        persistCommands(savedRun, commandsNode(data));
        log.info("AI dispatch 결과 저장 완료: runId={}, requestId={}, status={}, commandCount={}",
                savedRun.getId(), savedRun.getRequestId(), savedRun.getStatus(), savedRun.getCommandCount());
        return savedRun;
    }

    private void persistCommands(AiDispatchRun run, JsonNode commandsNode) {
        if (commandsNode == null || !commandsNode.isArray()) {
            return;
        }

        List<AiDispatchCommand> commands = new ArrayList<>();
        int commandIndex = 0;
        for (JsonNode commandNode : commandsNode) {
            commands.add(AiDispatchCommand.builder()
                    .dispatchRun(run)
                    .commandIndex(commandIndex++)
                    .hour(integerAt(commandNode, "/hour"))
                    .stationId(textAt(commandNode, "/station_id"))
                    .shareEnergyKwh(doubleAt(commandNode, "/share_energy_kwh"))
                    .essAction(doubleAt(commandNode, "/ess_action"))
                    .rawEssAction(doubleAt(commandNode, "/raw_ess_action"))
                    .pvPriority(doubleAt(commandNode, "/pv_priority"))
                    .socBefore(doubleAt(commandNode, "/soc_before"))
                    .socAfter(doubleAt(commandNode, "/soc_after"))
                    .gridTotalKwh(doubleAt(commandNode, "/grid_total_kwh"))
                    .gridCost(doubleAt(commandNode, "/grid_cost"))
                    .command(textAt(commandNode, "/command"))
                    .safetyAdjusted(booleanAt(commandNode, "/safety_adjusted"))
                    .commandPayload(toJson(commandNode))
                    .build());
        }
        dispatchCommandRepository.saveAll(commands);
    }

    private JsonNode commandsNode(JsonNode data) {
        if (data == null) {
            return null;
        }
        JsonNode commands = data.at("/dispatch/commands");
        return isUsable(commands) ? commands : null;
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (RuntimeException exception) {
            throw new IllegalStateException("AI dispatch payload JSON 직렬화에 실패했습니다.", exception);
        }
    }

    private LocalDate parseTargetDate(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return LocalDate.parse(value);
        } catch (DateTimeParseException ignored) {
            return null;
        }
    }

    private String textAt(JsonNode node, String pointer) {
        if (node == null) {
            return null;
        }
        JsonNode value = node.at(pointer);
        return isUsable(value) ? value.asText() : null;
    }

    private String firstTextAt(JsonNode node, String... pointers) {
        for (String pointer : pointers) {
            String value = textAt(node, pointer);
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }

    private Integer integerAt(JsonNode node, String pointer) {
        if (node == null) {
            return null;
        }
        JsonNode value = node.at(pointer);
        return isUsable(value) ? value.asInt() : null;
    }

    private Double doubleAt(JsonNode node, String pointer) {
        if (node == null) {
            return null;
        }
        JsonNode value = node.at(pointer);
        return isUsable(value) ? value.asDouble() : null;
    }

    private Boolean booleanAt(JsonNode node, String pointer) {
        if (node == null) {
            return null;
        }
        JsonNode value = node.at(pointer);
        return isUsable(value) ? value.asBoolean() : null;
    }

    private boolean isUsable(JsonNode node) {
        return node != null && !node.isMissingNode() && !node.isNull();
    }

    private String firstNonBlank(String primary, String fallback) {
        if (primary != null && !primary.isBlank()) {
            return primary;
        }
        return fallback;
    }
}
