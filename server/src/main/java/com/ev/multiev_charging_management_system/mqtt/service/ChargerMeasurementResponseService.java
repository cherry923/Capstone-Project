package com.ev.multiev_charging_management_system.mqtt.service;

import com.ev.multiev_charging_management_system.mqtt.dto.ChargerMeasurementResponse;
import com.ev.multiev_charging_management_system.mqtt.entity.ChargerMeasurementHistory;
import com.ev.multiev_charging_management_system.mqtt.repository.ChargerMeasurementRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Comparator;
import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ChargerMeasurementResponseService {

    private final ChargerMeasurementRepository chargerMeasurementRepository;
    private final ChargerMeasurementCacheService chargerMeasurementCacheService;

    public List<ChargerMeasurementResponse> getLatestSnapshot() {
        List<ChargerMeasurementResponse> cachedSnapshot =
                chargerMeasurementCacheService.getLatestSnapshot();
        if (cachedSnapshot.size() >= ChargerMeasurementCacheService.LATEST_SNAPSHOT_LIMIT) {
            return cachedSnapshot;
        }

        List<ChargerMeasurementHistory> dbSnapshot =
                chargerMeasurementRepository.findTop11ByOrderByIdDesc()
                        .stream()
                        .sorted(Comparator.comparing(ChargerMeasurementHistory::getId))
                        .toList();

        chargerMeasurementCacheService.cacheLatestSnapshot(dbSnapshot);

        return dbSnapshot.stream()
                .map(ChargerMeasurementResponse::from)
                .toList();
    }

    public List<ChargerMeasurementResponse> getChangesAfterId(Long afterId) {
        return chargerMeasurementRepository.findByIdGreaterThanOrderByIdAsc(afterId)
                .stream()
                .map(ChargerMeasurementResponse::from)
                .toList();
    }

    public List<ChargerMeasurementResponse> getChangesAfterId(
            String stationId,
            Integer chargerNo,
            Long afterId
    ) {
        return chargerMeasurementRepository
                .findByStationIdAndChargerNoAndIdGreaterThanOrderByIdAsc(
                        stationId,
                        chargerNo,
                        afterId
                )
                .stream()
                .map(ChargerMeasurementResponse::from)
                .toList();
    }
}
