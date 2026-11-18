package com.ev.multiev_charging_management_system.external.ai.timelapse.service;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class DashboardTimelapseDataInitializer implements ApplicationRunner {

    private final DashboardTimelapsePeriodService timelapsePeriodService;

    @Value("${app.dashboard.timelapse.seed-demo-enabled:true}")
    private boolean seedDemoEnabled;

    @Override
    public void run(ApplicationArguments args) {
        if (seedDemoEnabled) {
            timelapsePeriodService.seedDefaultPeriodIfMissing();
        }
    }
}
