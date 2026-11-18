package com.ev.multiev_charging_management_system.external.ai.dispatch.repository;

import com.ev.multiev_charging_management_system.external.ai.dispatch.entity.AiDispatchRun;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface AiDispatchRunRepository extends JpaRepository<AiDispatchRun, Long> {

    Optional<AiDispatchRun> findTopByOrderByCreatedAtDesc();
}
