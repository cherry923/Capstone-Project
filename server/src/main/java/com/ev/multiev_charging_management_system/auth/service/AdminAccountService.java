package com.ev.multiev_charging_management_system.auth.service;

import com.ev.multiev_charging_management_system.auth.dto.AdminStationResponse;
import com.ev.multiev_charging_management_system.auth.entity.AdminAccount;
import com.ev.multiev_charging_management_system.auth.entity.AdminChargingStation;
import com.ev.multiev_charging_management_system.auth.repository.AdminAccountRepository;
import com.ev.multiev_charging_management_system.auth.repository.AdminChargingStationRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class AdminAccountService {

    private final AdminAccountRepository adminAccountRepository;
    private final AdminChargingStationRepository adminChargingStationRepository;
    private final PasswordEncoder passwordEncoder;

    @Transactional
    public AdminAccount signup(String username, String rawPassword) {
        validateCredentials(username, rawPassword);
        String normalizedUsername = username.trim();
        if (adminAccountRepository.existsByUsername(normalizedUsername)) {
            throw new DuplicateAdminUsernameException(normalizedUsername);
        }

        AdminAccount account = adminAccountRepository.save(
                AdminAccount.create(normalizedUsername, passwordEncoder.encode(rawPassword))
        );
        createDefaultStations(account);
        return account;
    }

    @Transactional(readOnly = true)
    public AdminAccount login(String username, String rawPassword) {
        validateCredentials(username, rawPassword);
        AdminAccount account = adminAccountRepository.findByUsername(username.trim())
                .orElseThrow(InvalidAdminCredentialsException::new);

        if (!passwordEncoder.matches(rawPassword, account.getPasswordHash())) {
            throw new InvalidAdminCredentialsException();
        }

        return account;
    }

    @Transactional(readOnly = true)
    public boolean existsUsername(String username) {
        if (username == null || username.isBlank()) {
            return false;
        }
        return adminAccountRepository.existsByUsername(username.trim());
    }

    @Transactional(readOnly = true)
    public List<AdminStationResponse> getStations(String username) {
        if (username == null || username.isBlank()) {
            throw new IllegalArgumentException("관리자 ID가 필요합니다.");
        }

        return adminChargingStationRepository
                .findByAdminUsernameOrderByStationIdAsc(username.trim())
                .stream()
                .map(AdminStationResponse::from)
                .toList();
    }

    @Transactional
    public AdminStationResponse addStation(
            String username,
            String stationId,
            String stationName,
            String region
    ) {
        validateStation(username, stationId, stationName, region);
        String normalizedUsername = username.trim();
        String normalizedStationId = stationId.trim();

        AdminAccount account = adminAccountRepository.findByUsername(normalizedUsername)
                .orElseThrow(() -> new IllegalArgumentException("관리자 계정을 찾을 수 없습니다."));

        if (adminChargingStationRepository.existsByAdminUsernameAndStationId(
                normalizedUsername,
                normalizedStationId
        )) {
            throw new DuplicateAdminStationException(normalizedStationId);
        }

        AdminChargingStation station = adminChargingStationRepository.save(
                AdminChargingStation.create(
                        account,
                        normalizedStationId,
                        stationName.trim(),
                        region.trim(),
                        null,
                        null,
                        "ACTIVE"
                )
        );
        return AdminStationResponse.from(station);
    }

    @Transactional
    public void removeStation(String username, String stationId) {
        if (username == null || username.isBlank() || stationId == null || stationId.isBlank()) {
            throw new IllegalArgumentException("관리자 ID와 충전소 ID가 필요합니다.");
        }

        String normalizedUsername = username.trim();
        String normalizedStationId = stationId.trim();
        if (!adminChargingStationRepository.existsByAdminUsernameAndStationId(
                normalizedUsername,
                normalizedStationId
        )) {
            throw new AdminStationNotFoundException(normalizedStationId);
        }

        adminChargingStationRepository.deleteByAdminUsernameAndStationId(
                normalizedUsername,
                normalizedStationId
        );
    }

    @Transactional
    public void ensureDefaultAdmin(String username, String rawPassword) {
        if (username == null || username.isBlank() || rawPassword == null || rawPassword.isBlank()) {
            return;
        }
        if (adminAccountRepository.existsByUsername(username)) {
            ensureDefaultStations(username);
            return;
        }
        signup(username, rawPassword);
    }

    private void ensureDefaultStations(String username) {
        if (adminChargingStationRepository.existsByAdminUsername(username)) {
            return;
        }
        adminAccountRepository.findByUsername(username).ifPresent(this::createDefaultStations);
    }

    private void createDefaultStations(AdminAccount account) {
        adminChargingStationRepository.saveAll(List.of(
                AdminChargingStation.create(account, "1", "서울 강남 허브", "서울 강남구", 37.4979, 127.0276, "ACTIVE"),
                AdminChargingStation.create(account, "2", "서울 마포 스테이션", "서울 마포구", 37.5663, 126.9019, "ACTIVE"),
                AdminChargingStation.create(account, "3", "서울 송파 에너지 파크", "서울 송파구", 37.5145, 127.1059, "ACTIVE")
        ));
    }

    private void validateCredentials(String username, String rawPassword) {
        if (username == null || username.isBlank() || rawPassword == null || rawPassword.isBlank()) {
            throw new IllegalArgumentException("관리자 ID와 비밀번호를 입력하세요.");
        }
        if (username.trim().length() > 60) {
            throw new IllegalArgumentException("관리자 ID는 60자 이하로 입력하세요.");
        }
    }

    private void validateStation(String username, String stationId, String stationName, String region) {
        if (username == null || username.isBlank()) {
            throw new IllegalArgumentException("관리자 ID가 필요합니다.");
        }
        if (stationId == null || stationId.isBlank()) {
            throw new IllegalArgumentException("충전소 ID를 입력하세요.");
        }
        if (stationName == null || stationName.isBlank()) {
            throw new IllegalArgumentException("충전소명을 입력하세요.");
        }
        if (region == null || region.isBlank()) {
            throw new IllegalArgumentException("지역을 입력하세요.");
        }
        if (stationId.trim().length() > 100) {
            throw new IllegalArgumentException("충전소 ID는 100자 이하로 입력하세요.");
        }
    }

    public static class DuplicateAdminUsernameException extends RuntimeException {
        public DuplicateAdminUsernameException(String username) {
            super("이미 사용 중인 관리자 ID입니다: " + username);
        }
    }

    public static class InvalidAdminCredentialsException extends RuntimeException {
        public InvalidAdminCredentialsException() {
            super("관리자 ID 또는 비밀번호가 올바르지 않습니다.");
        }
    }

    public static class DuplicateAdminStationException extends RuntimeException {
        public DuplicateAdminStationException(String stationId) {
            super("이미 등록된 충전소입니다: " + stationId);
        }
    }

    public static class AdminStationNotFoundException extends RuntimeException {
        public AdminStationNotFoundException(String stationId) {
            super("등록된 충전소를 찾을 수 없습니다: " + stationId);
        }
    }
}
