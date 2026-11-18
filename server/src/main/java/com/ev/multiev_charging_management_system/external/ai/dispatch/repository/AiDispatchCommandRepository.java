package com.ev.multiev_charging_management_system.external.ai.dispatch.repository;

import com.ev.multiev_charging_management_system.external.ai.dispatch.entity.AiDispatchCommand;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AiDispatchCommandRepository extends JpaRepository<AiDispatchCommand, Long> {

    List<AiDispatchCommand> findByDispatchRunIdOrderByCommandIndexAsc(Long dispatchRunId);

    List<AiDispatchCommand> findByDispatchRunIdAndHourOrderByStationIdAsc(
            Long dispatchRunId,
            Integer hour
    );
}
