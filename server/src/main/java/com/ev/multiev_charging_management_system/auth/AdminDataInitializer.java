package com.ev.multiev_charging_management_system.auth;

import com.ev.multiev_charging_management_system.auth.service.AdminAccountService;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class AdminDataInitializer implements ApplicationRunner {

    private final AdminAccountService adminAccountService;

    @Value("${app.admin.username:admin}")
    private String defaultUsername;

    @Value("${app.admin.password:admin1234}")
    private String defaultPassword;

    @Override
    public void run(ApplicationArguments args) {
        adminAccountService.ensureDefaultAdmin(defaultUsername, defaultPassword);
    }
}
