package com.ev.multiev_charging_management_system.mqtt.service;

import com.ev.multiev_charging_management_system.mqtt.entity.ChargerMeasurementFailedHistory;
import com.ev.multiev_charging_management_system.mqtt.repository.ChargerMeasurementFailedRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class ChargerMeasurementFailedService {

    private final ChargerMeasurementFailedRepository repository;

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void saveFailedMessage(String topic, String payload, Exception e) {
        repository.save(ChargerMeasurementFailedHistory.of(topic, payload, e));
    }
}
