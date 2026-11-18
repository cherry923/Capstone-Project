package com.ev.multiev_charging_management_system.auth.repository;

import com.ev.multiev_charging_management_system.auth.entity.AdminChargingStation;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AdminChargingStationRepository extends JpaRepository<AdminChargingStation, Long> {

    List<AdminChargingStation> findByAdminUsernameOrderByStationIdAsc(String username);

    boolean existsByAdminUsername(String username);

    boolean existsByAdminUsernameAndStationId(String username, String stationId);

    void deleteByAdminUsernameAndStationId(String username, String stationId);
}
