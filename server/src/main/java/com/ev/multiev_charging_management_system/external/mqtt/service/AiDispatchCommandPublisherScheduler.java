package com.ev.multiev_charging_management_system.external.mqtt.service;

import com.ev.multiev_charging_management_system.external.ai.dispatch.entity.AiDispatchCommand;
import com.ev.multiev_charging_management_system.external.ai.dispatch.entity.AiDispatchRun;
import com.ev.multiev_charging_management_system.external.ai.dispatch.repository.AiDispatchCommandRepository;
import com.ev.multiev_charging_management_system.external.ai.dispatch.repository.AiDispatchRunRepository;
import com.ev.multiev_charging_management_system.external.ai.dispatch.service.AiDispatchPersistenceService;
import lombok.RequiredArgsConstructor;
import org.springframework.integration.mqtt.support.MqttHeaders;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.List;

/**
 * 최신 AI 디스패치 실행 결과를 기준으로 현재 시간대의 제어 명령을 MQTT로 발행하는 스케줄러 객체.
 *
 * <p>매 정각마다 가장 최근에 생성된 AI 디스패치 실행 이력을 조회하고,
 * 현재 시각에 해당하는 충전소별 명령만 가져와 MQTT 발행 서비스에 전달한다.
 */
@Service
@RequiredArgsConstructor
public class AiDispatchCommandPublisherScheduler {

    private final AiDispatchRunRepository dispatchRunRepository;
    private final AiDispatchCommandRepository dispatchCommandRepository;
    private final AiDispatchCommandMqttPublisher aiDispatchCommandMqttPublisher;

    /**
     * 매 정각마다 현재 시간대의 AI 디스패치 명령을 조회하여 MQTT로 발행한다.
     *
     * <p>최신 디스패치 실행 이력이 없으면 아무 작업도 수행하지 않는다.
     */
    @Scheduled(cron = "0 0 * * * *", zone = "Asia/Seoul")
    public void publishCurrentHourCommands() {

        AiDispatchRun latestRun = dispatchRunRepository.findTopByOrderByCreatedAtDesc()
                .orElse(null);

        if (latestRun == null) {
            return;
        }

        int currentHour = LocalDateTime.now(ZoneId.of("Asia/Seoul")).getHour();

        List<AiDispatchCommand> commands =
                dispatchCommandRepository.findByDispatchRunIdAndHourOrderByStationIdAsc(
                        latestRun.getId(),
                        currentHour
                );

        aiDispatchCommandMqttPublisher.publish(commands);
    }
}
