package com.ev.multiev_charging_management_system.auth;

import com.ev.multiev_charging_management_system.auth.dto.AdminStationResponse;
import com.ev.multiev_charging_management_system.auth.service.AdminAccountService;
import com.ev.multiev_charging_management_system.auth.service.AdminAccountService.AdminStationNotFoundException;
import com.ev.multiev_charging_management_system.auth.service.AdminAccountService.DuplicateAdminStationException;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequiredArgsConstructor
@RequestMapping({"/api/admin/stations", "/api/v1/admin/stations"})
public class AdminStationController {

    private final AdminAccountService adminAccountService;

    @GetMapping
    public ResponseEntity<Map<String, Object>> getStations(@RequestParam String username) {
        List<AdminStationResponse> stations = adminAccountService.getStations(username);
        return ResponseEntity.ok(Map.of(
                "code", "SUCCESS",
                "message", "관리자 충전소 목록 조회가 완료되었습니다.",
                "data", Map.of(
                        "username", username,
                        "stations", stations
                )
        ));
    }

    @PostMapping
    public ResponseEntity<Map<String, Object>> addStation(
            @RequestParam String username,
            @RequestBody AdminStationRequest request
    ) {
        try {
            AdminStationResponse station = adminAccountService.addStation(
                    username,
                    request.stationId(),
                    request.stationName(),
                    request.region()
            );
            return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
                    "code", "SUCCESS",
                    "message", "충전소가 추가되었습니다.",
                    "data", station
            ));
        } catch (DuplicateAdminStationException exception) {
            return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of(
                    "code", "DUPLICATE_STATION",
                    "message", "이미 등록된 충전소입니다."
            ));
        } catch (IllegalArgumentException exception) {
            return ResponseEntity.badRequest().body(Map.of(
                    "code", "INVALID_REQUEST",
                    "message", exception.getMessage()
            ));
        }
    }

    @DeleteMapping("/{stationId}")
    public ResponseEntity<Map<String, Object>> removeStation(
            @RequestParam String username,
            @PathVariable String stationId
    ) {
        try {
            adminAccountService.removeStation(username, stationId);
            return ResponseEntity.ok(Map.of(
                    "code", "SUCCESS",
                    "message", "충전소가 제거되었습니다.",
                    "data", Map.of(
                            "username", username,
                            "stationId", stationId
                    )
            ));
        } catch (AdminStationNotFoundException exception) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of(
                    "code", "STATION_NOT_FOUND",
                    "message", "등록된 충전소를 찾을 수 없습니다."
            ));
        } catch (IllegalArgumentException exception) {
            return ResponseEntity.badRequest().body(Map.of(
                    "code", "INVALID_REQUEST",
                    "message", exception.getMessage()
            ));
        }
    }

    public record AdminStationRequest(
            String stationId,
            String stationName,
            String region
    ) {
    }
}
