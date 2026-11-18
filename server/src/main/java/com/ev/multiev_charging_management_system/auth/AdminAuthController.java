package com.ev.multiev_charging_management_system.auth;

import com.ev.multiev_charging_management_system.auth.entity.AdminAccount;
import com.ev.multiev_charging_management_system.auth.service.AdminAccountService;
import com.ev.multiev_charging_management_system.auth.service.AdminAccountService.DuplicateAdminUsernameException;
import com.ev.multiev_charging_management_system.auth.service.AdminAccountService.InvalidAdminCredentialsException;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AdminAuthController {

    private final AdminAccountService adminAccountService;

    @PostMapping("/signup")
    public ResponseEntity<Map<String, Object>> signup(@RequestBody AdminAuthRequest request) {
        try {
            AdminAccount account = adminAccountService.signup(request.username(), request.password());
            return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
                    "code", "SUCCESS",
                    "message", "관리자 계정이 생성되었습니다.",
                    "data", Map.of("username", account.getUsername())
            ));
        } catch (DuplicateAdminUsernameException exception) {
            return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of(
                    "code", "DUPLICATE_USERNAME",
                    "message", "이미 사용 중인 관리자 ID입니다."
            ));
        } catch (IllegalArgumentException exception) {
            return ResponseEntity.badRequest().body(Map.of(
                    "code", "INVALID_REQUEST",
                    "message", exception.getMessage()
            ));
        }
    }

    @GetMapping("/check-username")
    public ResponseEntity<Map<String, Object>> checkUsername(@RequestParam String username) {
        boolean exists = adminAccountService.existsUsername(username);
        return ResponseEntity.ok(Map.of(
                "code", "SUCCESS",
                "message", exists ? "이미 사용 중인 관리자 ID입니다." : "사용 가능한 관리자 ID입니다.",
                "data", Map.of(
                        "username", username,
                        "available", !exists
                )
        ));
    }

    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody AdminAuthRequest request) {
        try {
            AdminAccount account = adminAccountService.login(request.username(), request.password());
            return ResponseEntity.ok(Map.of(
                    "code", "SUCCESS",
                    "message", "관리자 로그인이 완료되었습니다.",
                    "data", Map.of("username", account.getUsername())
            ));
        } catch (InvalidAdminCredentialsException exception) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of(
                    "code", "INVALID_CREDENTIALS",
                    "message", exception.getMessage()
            ));
        } catch (IllegalArgumentException exception) {
            return ResponseEntity.badRequest().body(Map.of(
                    "code", "INVALID_REQUEST",
                    "message", exception.getMessage()
            ));
        }
    }

    public record AdminAuthRequest(String username, String password) {
    }
}
