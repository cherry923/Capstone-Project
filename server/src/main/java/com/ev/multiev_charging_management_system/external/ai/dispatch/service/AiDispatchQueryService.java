package com.ev.multiev_charging_management_system.external.ai.dispatch.service;

import com.ev.multiev_charging_management_system.external.ai.dispatch.entity.AiDispatchCommand;
import com.ev.multiev_charging_management_system.external.ai.dispatch.entity.AiDispatchRun;
import com.ev.multiev_charging_management_system.external.ai.dispatch.repository.AiDispatchCommandRepository;
import com.ev.multiev_charging_management_system.external.ai.dispatch.repository.AiDispatchRunRepository;
import com.ev.multiev_charging_management_system.external.ai.dto.AiDispatchRunQueryResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.ObjectMapper;

import java.util.List;

import static org.springframework.http.HttpStatus.NOT_FOUND;

@Service
@RequiredArgsConstructor
public class AiDispatchQueryService {

    private static final int MAX_RECENT_RUNS = 50;

    private final AiDispatchRunRepository dispatchRunRepository;
    private final AiDispatchCommandRepository dispatchCommandRepository;
    private final ObjectMapper objectMapper;

    @Transactional(readOnly = true)
    public List<AiDispatchRunQueryResponse.Summary> recentRuns(int limit) {
        int safeLimit = Math.max(1, Math.min(limit, MAX_RECENT_RUNS));
        return dispatchRunRepository.findAll(
                        PageRequest.of(0, safeLimit, Sort.by(Sort.Direction.DESC, "createdAt"))
                ).stream()
                .map(this::toSummary)
                .toList();
    }

    @Transactional(readOnly = true)
    public AiDispatchRunQueryResponse.Detail latestRun() {
        AiDispatchRun run = dispatchRunRepository.findTopByOrderByCreatedAtDesc()
                .orElseThrow(() -> new ResponseStatusException(NOT_FOUND, "AI dispatch run not found."));
        return detail(run);
    }

    @Transactional(readOnly = true)
    public AiDispatchRunQueryResponse.Detail getRun(Long runId) {
        AiDispatchRun run = dispatchRunRepository.findById(runId)
                .orElseThrow(() -> new ResponseStatusException(NOT_FOUND, "AI dispatch run not found."));
        return detail(run);
    }

    private AiDispatchRunQueryResponse.Detail detail(AiDispatchRun run) {
        List<AiDispatchRunQueryResponse.Command> commands = dispatchCommandRepository
                .findByDispatchRunIdOrderByCommandIndexAsc(run.getId())
                .stream()
                .map(this::toCommand)
                .toList();

        return new AiDispatchRunQueryResponse.Detail(
                toSummary(run),
                commands,
                parseJsonOrRaw(run.getRequestPayload()),
                parseJsonOrRaw(run.getResponsePayload())
        );
    }

    private AiDispatchRunQueryResponse.Summary toSummary(AiDispatchRun run) {
        return new AiDispatchRunQueryResponse.Summary(
                run.getId(),
                run.getRequestId(),
                run.getTargetDate(),
                run.getStatus(),
                run.getMessage(),
                run.getModelVersion(),
                run.getModelName(),
                run.getModelStatus(),
                run.getPvSource(),
                run.getEvSource(),
                run.getTeamModelSource(),
                run.getCommandCount(),
                run.getCreatedAt()
        );
    }

    private AiDispatchRunQueryResponse.Command toCommand(AiDispatchCommand command) {
        return new AiDispatchRunQueryResponse.Command(
                command.getCommandIndex(),
                command.getHour(),
                command.getStationId(),
                command.getShareEnergyKwh(),
                command.getEssAction(),
                command.getRawEssAction(),
                command.getPvPriority(),
                command.getSocBefore(),
                command.getSocAfter(),
                command.getGridTotalKwh(),
                command.getGridCost(),
                command.getCommand(),
                command.getSafetyAdjusted(),
                parseJsonOrRaw(command.getCommandPayload())
        );
    }

    private Object parseJsonOrRaw(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readTree(value);
        } catch (RuntimeException ignored) {
            return value;
        }
    }
}
